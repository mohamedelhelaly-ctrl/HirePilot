"""
Follow-up Question Prompt Builders

Two separate prompts — one for HR/behavioral/final interviews,
one for technical interviews.

Called every 30 seconds during the live interview loop when
enough new transcript content has accumulated.
"""


def build_hr_followup_prompt(
    job_description: str,
    pre_generated_questions: list[str],
    transcript_so_far: str,
    last_followup: str | None,
) -> str:
    questions_str = (
        "\n".join(f"- {q}" for q in pre_generated_questions)
        if pre_generated_questions
        else "No pre-generated questions — use your judgment based on the job description and transcript."
    )
    last_q = f'The last follow-up you suggested was: "{last_followup}"' \
        if last_followup else "No follow-up questions have been suggested yet."

    system = """\
You are an expert HR interviewer assistant providing real-time coaching during a live interview.

Based on the interview transcript so far, suggest ONE concise follow-up question
that digs deeper into the candidate's competencies, behavioral indicators, or
areas that need clarification.

Rules:
- Ask only ONE question.
- Do not repeat a question already asked.
- Keep it conversational and natural.
- Focus on STAR (Situation, Task, Action, Result) probing if an answer was vague.
- Return ONLY the question text — no preamble, no explanation, no punctuation beyond the question mark."""

    user = f"""JOB DESCRIPTION: {job_description[:400]}

PRE-GENERATED QUESTIONS FOR THIS INTERVIEW:
{questions_str}

{last_q}

TRANSCRIPT SO FAR:
{transcript_so_far[-3000:]}

Suggest one follow-up question:"""

    return f"SYSTEM:\n{system}\n\nUSER:\n{user}"


def build_technical_followup_prompt(
    job_description: str,
    pre_generated_questions: list[str],
    transcript_so_far: str,
    last_followup: str | None,
) -> str:
    questions_str = (
        "\n".join(f"- {q}" for q in pre_generated_questions)
        if pre_generated_questions
        else "No pre-generated questions — use your judgment based on the job description and transcript."
    )
    last_q = f'The last follow-up you suggested was: "{last_followup}"' \
        if last_followup else "No follow-up questions have been suggested yet."

    system = """\
You are an expert technical interviewer assistant providing real-time coaching during a live technical interview.

Based on the interview transcript so far, suggest ONE concise technical follow-up question
that probes deeper into the candidate's technical understanding, practical experience,
or clarifies an incomplete/vague technical answer.

Rules:
- Ask only ONE question.
- Do not repeat a question already asked.
- Focus on technical depth: implementation details, trade-offs, edge cases, debugging approaches.
- If the candidate gave a surface-level answer, probe for underlying principles.
- Return ONLY the question text — no preamble, no explanation, no punctuation beyond the question mark."""

    user = f"""JOB DESCRIPTION: {job_description[:400]}

PRE-GENERATED TECHNICAL QUESTIONS FOR THIS INTERVIEW:
{questions_str}

{last_q}

TRANSCRIPT SO FAR:
{transcript_so_far[-3000:]}

Suggest one technical follow-up question:"""

    return f"SYSTEM:\n{system}\n\nUSER:\n{user}"


def build_followup_prompt(
    interview_type: str,
    job_description: str,
    pre_generated_questions: list[str],
    transcript_so_far: str,
    last_followup: str | None,
) -> str:
    """
    Route to the correct prompt builder based on interview type.

    Args:
        interview_type: "hr_screen" | "technical" | "behavioral" | "final"
    """
    if interview_type == "technical":
        return build_technical_followup_prompt(
            job_description, pre_generated_questions,
            transcript_so_far, last_followup,
        )
    return build_hr_followup_prompt(
        job_description, pre_generated_questions,
        transcript_so_far, last_followup,
    )