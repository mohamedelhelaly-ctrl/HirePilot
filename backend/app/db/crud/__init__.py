# Import all CRUD submodules for organization
from . import user_crud
from . import requisition_crud
from . import candidate_crud
from . import application_crud
from . import application_detail_crud
from . import screening_result_crud
from . import interview_session_crud
from . import transcript_chunk_crud
from . import status_history_crud
from . import webhook_event_crud
from . import refresh_token_crud

# Re-export all functions for backward compatibility with existing imports
# This allows code to do: from db import crud; crud.create_user(...)

# User CRUD
from .user_crud import (
    create_user,
    get_user_by_id,
    get_user_by_email,
    get_users,
    update_user,
)

# Requisition CRUD
from .requisition_crud import (
    create_requisition,
    get_requisition_by_id,
    get_requisition_by_lever_id,
    get_requisitions,
    update_requisition,
    increment_requisition_counter,
    reset_requisition_counter,
)

# Candidate CRUD
from .candidate_crud import (
    create_candidate,
    get_candidate_by_id,
    get_candidate_by_lever_id,
    get_candidate_by_email,
    get_or_create_candidate,
)

# Application CRUD
from .application_crud import (
    create_application,
    get_application_by_id,
    get_application_by_lever_opportunity_id,
    get_applications_by_requisition,
    update_application,
    update_application_status,
)

# Application Detail CRUD
from .application_detail_crud import (
    create_application_detail,
    create_application_details_bulk,
    get_application_details,
)

# Screening Result CRUD
from .screening_result_crud import (
    create_screening_result,
    get_screening_result_by_application,
    update_screening_result,
)

# Interview Session CRUD
from .interview_session_crud import (
    create_interview_session,
    get_interview_session_by_id,
    get_interview_sessions_by_application,
    update_interview_session,
)

# Transcript Chunk CRUD
from .transcript_chunk_crud import (
    create_transcript_chunk,
    get_transcript_chunks_by_session,
)

# Status History CRUD
from .status_history_crud import (
    create_status_history,
    get_status_history_by_application,
)

# Webhook Event CRUD
from .webhook_event_crud import (
    create_webhook_event,
    get_webhook_event_by_lever_id,
    get_unprocessed_webhook_events,
    update_webhook_event,
)

# Refresh Token CRUD
from .refresh_token_crud import (
    create_refresh_token,
    get_refresh_token_by_hash,
    delete_refresh_token,
    delete_expired_refresh_tokens,
    delete_user_refresh_tokens,
)

__all__ = [
    # Submodules
    "user_crud",
    "requisition_crud",
    "candidate_crud",
    "application_crud",
    "application_detail_crud",
    "screening_result_crud",
    "interview_session_crud",
    "transcript_chunk_crud",
    "status_history_crud",
    "webhook_event_crud",
    "refresh_token_crud",
    # Re-exported functions for backward compatibility
    "create_user",
    "get_user_by_id",
    "get_user_by_email",
    "get_users",
    "update_user",
    "create_requisition",
    "get_requisition_by_id",
    "get_requisition_by_lever_id",
    "get_requisitions",
    "update_requisition",
    "increment_requisition_counter",
    "reset_requisition_counter",
    "create_candidate",
    "get_candidate_by_id",
    "get_candidate_by_lever_id",
    "get_candidate_by_email",
    "get_or_create_candidate",
    "create_application",
    "get_application_by_id",
    "get_application_by_lever_opportunity_id",
    "get_applications_by_requisition",
    "update_application",
    "update_application_status",
    "create_application_detail",
    "create_application_details_bulk",
    "get_application_details",
    "create_screening_result",
    "get_screening_result_by_application",
    "update_screening_result",
    "create_interview_session",
    "get_interview_session_by_id",
    "get_interview_sessions_by_application",
    "update_interview_session",
    "create_transcript_chunk",
    "get_transcript_chunks_by_session",
    "create_status_history",
    "get_status_history_by_application",
    "create_webhook_event",
    "get_webhook_event_by_lever_id",
    "get_unprocessed_webhook_events",
    "update_webhook_event",
    "create_refresh_token",
    "get_refresh_token_by_hash",
    "delete_refresh_token",
    "delete_expired_refresh_tokens",
    "delete_user_refresh_tokens",
]
