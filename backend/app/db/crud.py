from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, func
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Any
from datetime import datetime, timedelta
import bcrypt

from .models import (
    User, Requisition, Candidate, Application, ApplicationDetail,
    ScreeningResult, InterviewSession, TranscriptChunk, StatusHistory,
    WebhookEvent, RefreshToken, ApplicationStatus, InterviewStatus
)
from schemas import (
    UserCreate, UserUpdate, RequisitionCreate, RequisitionUpdate,
    CandidateCreate, CandidateUpdate, ApplicationCreate, ApplicationUpdate,
    ApplicationDetailCreate, ScreeningResultCreate, ScreeningResultUpdate,
    InterviewSessionCreate, InterviewSessionUpdate, TranscriptChunkCreate,
    StatusHistoryCreate, WebhookEventCreate, WebhookEventUpdate
)


# ============================================================================
# USER CRUD
# ============================================================================

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Create a new user with hashed password."""
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Get all users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Update user information."""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# ============================================================================
# REQUISITION CRUD
# ============================================================================

async def create_requisition(db: AsyncSession, requisition: RequisitionCreate) -> Requisition:
    """Create a new requisition."""
    db_requisition = Requisition(**requisition.model_dump())
    db.add(db_requisition)
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def get_requisition_by_id(db: AsyncSession, requisition_id: int) -> Optional[Requisition]:
    """Get requisition by ID."""
    result = await db.execute(select(Requisition).where(Requisition.id == requisition_id))
    return result.scalar_one_or_none()


async def get_requisition_by_lever_id(db: AsyncSession, lever_id: str) -> Optional[Requisition]:
    """Get requisition by Lever ID."""
    result = await db.execute(select(Requisition).where(Requisition.lever_id == lever_id))
    return result.scalar_one_or_none()


async def get_requisitions(
    db: AsyncSession,
    hiring_manager_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Requisition]:
    """Get requisitions with optional filters."""
    query = select(Requisition)
    
    if hiring_manager_id is not None:
        query = query.where(Requisition.hiring_manager_id == hiring_manager_id)
    if is_active is not None:
        query = query.where(Requisition.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(desc(Requisition.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_requisition(
    db: AsyncSession,
    requisition_id: int,
    requisition_update: RequisitionUpdate
) -> Optional[Requisition]:
    """Update requisition information."""
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    update_data = requisition_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_requisition, field, value)
    
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def increment_requisition_counter(
    db: AsyncSession,
    requisition_id: int,
    counter_type: str  # "candidate", "assessment", "interview"
) -> Optional[Requisition]:
    """Increment a specific counter and return the requisition."""
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    if counter_type == "candidate":
        db_requisition.new_candidate_counter += 1
    elif counter_type == "assessment":
        db_requisition.new_assessment_counter += 1
    elif counter_type == "interview":
        db_requisition.new_interview_counter += 1
    
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def reset_requisition_counter(
    db: AsyncSession,
    requisition_id: int,
    counter_type: str
) -> Optional[Requisition]:
    """Reset a specific counter to zero."""
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    if counter_type == "candidate":
        db_requisition.new_candidate_counter = 0
    elif counter_type == "assessment":
        db_requisition.new_assessment_counter = 0
    elif counter_type == "interview":
        db_requisition.new_interview_counter = 0
    
    db_requisition.last_screening_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


# ============================================================================
# CANDIDATE CRUD
# ============================================================================

async def create_candidate(db: AsyncSession, candidate: CandidateCreate) -> Candidate:
    """Create a new candidate."""
    db_candidate = Candidate(**candidate.model_dump())
    db.add(db_candidate)
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate


async def get_candidate_by_id(db: AsyncSession, candidate_id: int) -> Optional[Candidate]:
    """Get candidate by ID."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()


async def get_candidate_by_lever_id(db: AsyncSession, lever_id: str) -> Optional[Candidate]:
    """Get candidate by Lever ID."""
    result = await db.execute(select(Candidate).where(Candidate.lever_id == lever_id))
    return result.scalar_one_or_none()


async def get_candidate_by_email(db: AsyncSession, email: str) -> Optional[Candidate]:
    """Get candidate by email."""
    result = await db.execute(select(Candidate).where(Candidate.email == email))
    return result.scalar_one_or_none()


async def get_or_create_candidate(db: AsyncSession, candidate: CandidateCreate) -> Candidate:
    """Get existing candidate by lever_id or create new one."""
    db_candidate = await get_candidate_by_lever_id(db, candidate.lever_id)
    if db_candidate:
        return db_candidate
    return await create_candidate(db, candidate)


# ============================================================================
# APPLICATION CRUD
# ============================================================================

async def create_application(db: AsyncSession, application: ApplicationCreate) -> Application:
    """Create a new application."""
    db_application = Application(**application.model_dump())
    db.add(db_application)
    await db.commit()
    await db.refresh(db_application)
    return db_application


async def get_application_by_id(
    db: AsyncSession,
    application_id: int,
    include_relations: bool = False
) -> Optional[Application]:
    """Get application by ID, optionally with related data."""
    query = select(Application).where(Application.id == application_id)
    
    if include_relations:
        query = query.options(
            joinedload(Application.candidate),
            joinedload(Application.screening_result),
            selectinload(Application.interview_sessions),
            selectinload(Application.details)
        )
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_application_by_lever_opportunity_id(
    db: AsyncSession,
    lever_opportunity_id: str
) -> Optional[Application]:
    """Get application by Lever opportunity ID."""
    result = await db.execute(
        select(Application).where(Application.lever_opportunity_id == lever_opportunity_id)
    )
    return result.scalar_one_or_none()


async def get_applications_by_requisition(
    db: AsyncSession,
    requisition_id: int,
    status: Optional[ApplicationStatus] = None,
    min_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    include_relations: bool = False
) -> List[Application]:
    """Get applications for a requisition with optional filters, ordered by combined score."""
    query = select(Application).where(Application.requisition_id == requisition_id)
    
    if status:
        query = query.where(Application.status == status)
    if min_score is not None:
        query = query.where(Application.combined_score >= min_score)
    
    if include_relations:
        query = query.options(
            joinedload(Application.candidate),
            joinedload(Application.screening_result)
        )
    
    query = query.order_by(desc(Application.combined_score)).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_application(
    db: AsyncSession,
    application_id: int,
    application_update: ApplicationUpdate
) -> Optional[Application]:
    """Update application information."""
    db_application = await get_application_by_id(db, application_id)
    if not db_application:
        return None
    
    update_data = application_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)
    
    db_application.last_activity_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_application)
    return db_application


async def update_application_status(
    db: AsyncSession,
    application_id: int,
    new_status: ApplicationStatus,
    user_id: Optional[int] = None,
    reason: Optional[str] = None
) -> Optional[Application]:
    """Update application status and create status history entry."""
    db_application = await get_application_by_id(db, application_id)
    if not db_application:
        return None
    
    old_status = db_application.status
    db_application.status = new_status
    db_application.last_activity_at = datetime.utcnow()
    
    # Create status history entry
    history_entry = StatusHistory(
        application_id=application_id,
        from_status=old_status,
        to_status=new_status,
        changed_by_user_id=user_id,
        reason=reason
    )
    db.add(history_entry)
    
    await db.commit()
    await db.refresh(db_application)
    return db_application


# ============================================================================
# APPLICATION DETAIL CRUD
# ============================================================================

async def create_application_detail(
    db: AsyncSession,
    detail: ApplicationDetailCreate
) -> ApplicationDetail:
    """Create a new application detail."""
    db_detail = ApplicationDetail(**detail.model_dump())
    db.add(db_detail)
    await db.commit()
    await db.refresh(db_detail)
    return db_detail


async def create_application_details_bulk(
    db: AsyncSession,
    details: List[ApplicationDetailCreate]
) -> List[ApplicationDetail]:
    """Create multiple application details in bulk."""
    db_details = [ApplicationDetail(**detail.model_dump()) for detail in details]
    db.add_all(db_details)
    await db.commit()
    return db_details


async def get_application_details(
    db: AsyncSession,
    application_id: int
) -> List[ApplicationDetail]:
    """Get all details for an application."""
    result = await db.execute(
        select(ApplicationDetail).where(ApplicationDetail.application_id == application_id)
    )
    return list(result.scalars().all())


# ============================================================================
# SCREENING RESULT CRUD
# ============================================================================

async def create_screening_result(
    db: AsyncSession,
    result: ScreeningResultCreate
) -> ScreeningResult:
    """Create a new screening result."""
    db_result = ScreeningResult(**result.model_dump())
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)
    return db_result


async def get_screening_result_by_application(
    db: AsyncSession,
    application_id: int
) -> Optional[ScreeningResult]:
    """Get screening result for an application."""
    result = await db.execute(
        select(ScreeningResult).where(ScreeningResult.application_id == application_id)
    )
    return result.scalar_one_or_none()


async def update_screening_result(
    db: AsyncSession,
    application_id: int,
    result_update: ScreeningResultUpdate
) -> Optional[ScreeningResult]:
    """Update screening result."""
    db_result = await get_screening_result_by_application(db, application_id)
    if not db_result:
        return None
    
    update_data = result_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_result, field, value)
    
    await db.commit()
    await db.refresh(db_result)
    return db_result


# ============================================================================
# INTERVIEW SESSION CRUD
# ============================================================================

async def create_interview_session(
    db: AsyncSession,
    session: InterviewSessionCreate
) -> InterviewSession:
    """Create a new interview session."""
    db_session = InterviewSession(**session.model_dump())
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session


async def get_interview_session_by_id(db: AsyncSession, session_id: int) -> Optional[InterviewSession]:
    """Get interview session by ID."""
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_interview_sessions_by_application(
    db: AsyncSession,
    application_id: int
) -> List[InterviewSession]:
    """Get all interview sessions for an application."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.application_id == application_id)
        .order_by(InterviewSession.scheduled_start_time)
    )
    return list(result.scalars().all())


async def update_interview_session(
    db: AsyncSession,
    session_id: int,
    session_update: InterviewSessionUpdate
) -> Optional[InterviewSession]:
    """Update interview session."""
    db_session = await get_interview_session_by_id(db, session_id)
    if not db_session:
        return None
    
    update_data = session_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)
    
    await db.commit()
    await db.refresh(db_session)
    return db_session


# ============================================================================
# TRANSCRIPT CHUNK CRUD
# ============================================================================

async def create_transcript_chunk(
    db: AsyncSession,
    chunk: TranscriptChunkCreate
) -> TranscriptChunk:
    """Create a new transcript chunk."""
    db_chunk = TranscriptChunk(**chunk.model_dump())
    db.add(db_chunk)
    await db.commit()
    await db.refresh(db_chunk)
    return db_chunk


async def get_transcript_chunks_by_session(
    db: AsyncSession,
    session_id: int
) -> List[TranscriptChunk]:
    """Get all transcript chunks for a session, ordered by sequence."""
    result = await db.execute(
        select(TranscriptChunk)
        .where(TranscriptChunk.session_id == session_id)
        .order_by(TranscriptChunk.sequence_number)
    )
    return list(result.scalars().all())


# ============================================================================
# STATUS HISTORY CRUD
# ============================================================================

async def create_status_history(
    db: AsyncSession,
    history: StatusHistoryCreate
) -> StatusHistory:
    """Create a new status history entry."""
    db_history = StatusHistory(**history.model_dump())
    db.add(db_history)
    await db.commit()
    await db.refresh(db_history)
    return db_history


async def get_status_history_by_application(
    db: AsyncSession,
    application_id: int
) -> List[StatusHistory]:
    """Get all status history for an application."""
    result = await db.execute(
        select(StatusHistory)
        .where(StatusHistory.application_id == application_id)
        .order_by(desc(StatusHistory.created_at))
    )
    return list(result.scalars().all())


# ============================================================================
# WEBHOOK EVENT CRUD
# ============================================================================

async def create_webhook_event(
    db: AsyncSession,
    event: WebhookEventCreate
) -> WebhookEvent:
    """Create a new webhook event."""
    db_event = WebhookEvent(**event.model_dump())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def get_webhook_event_by_lever_id(
    db: AsyncSession,
    lever_event_id: str
) -> Optional[WebhookEvent]:
    """Get webhook event by Lever event ID (for idempotency)."""
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.lever_event_id == lever_event_id)
    )
    return result.scalar_one_or_none()


async def get_unprocessed_webhook_events(
    db: AsyncSession,
    limit: int = 100
) -> List[WebhookEvent]:
    """Get unprocessed webhook events."""
    result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.processed == False)
        .order_by(WebhookEvent.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_webhook_event(
    db: AsyncSession,
    event_id: int,
    event_update: WebhookEventUpdate
) -> Optional[WebhookEvent]:
    """Update webhook event status."""
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.id == event_id)
    )
    db_event = result.scalar_one_or_none()
    if not db_event:
        return None
    
    update_data = event_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event, field, value)
    
    await db.commit()
    await db.refresh(db_event)
    return db_event


# ============================================================================
# REFRESH TOKEN CRUD
# ============================================================================

async def create_refresh_token(
    db: AsyncSession,
    user_id: int,
    token_hash: str,
    expires_at: datetime
) -> RefreshToken:
    """Create a new refresh token."""
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


async def get_refresh_token_by_hash(
    db: AsyncSession,
    token_hash: str
) -> Optional[RefreshToken]:
    """Get refresh token by hash."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token_hash: str) -> bool:
    """Delete a refresh token."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.commit()
    return result.rowcount > 0


async def delete_expired_refresh_tokens(db: AsyncSession) -> int:
    """Delete all expired refresh tokens."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
    )
    await db.commit()
    return result.rowcount


async def delete_user_refresh_tokens(db: AsyncSession, user_id: int) -> int:
    """Delete all refresh tokens for a user."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    await db.commit()
    return result.rowcount
