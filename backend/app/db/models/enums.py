import enum


class UserRole(str, enum.Enum):
    HR_MANAGER = "hr_manager"
    HIRING_MANAGER = "hiring_manager"


class ApplicationStatus(str, enum.Enum):
    NEW = "new"
    SCREENING_PENDING = "screening_pending"
    SCREENING_PASSED = "screening_passed"
    SCREENING_REJECTED = "screening_rejected"
    ASSESSMENT_SENT = "assessment_sent"
    ASSESSMENT_COMPLETED = "assessment_completed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_EXTENDED = "offer_extended"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class InterviewType(str, enum.Enum):
    HR_SCREEN = "hr_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    FINAL = "final"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
