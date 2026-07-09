"""Parse LLM output into structured interview question objects."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_array_from_text(text: str) -> list[dict[str, Any]] | None:
    if not text:
        return None

    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        candidate = text[first_bracket : last_bracket + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def parse_question_answer_pairs(text: str) -> list[dict[str, str]]:
    """Fallback parser for plain-text question/answer pairs."""
    questions: list[dict[str, str]] = []
    current_question = None
    current_answer: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        question_match = re.match(
            r"^(?:Q(?:uestion)?\s*\d*[:\.)]?\s*)(.+?)(?:\s*-\s*Answer[:\.]?)?$",
            stripped,
            flags=re.I,
        )
        answer_match = re.match(r"^(?:A(?:nswer)?\s*[:\.)]?\s*)(.+)$", stripped, flags=re.I)

        if question_match and not answer_match:
            if current_question and current_answer:
                questions.append({
                    "question": current_question,
                    "answer": " ".join(current_answer).strip(),
                })
            current_question = question_match.group(1).strip()
            current_answer = []
            continue

        if answer_match and current_question:
            current_answer.append(answer_match.group(1).strip())
            continue

        pair_match = re.match(r"^[-*]\s*(.+?):\s*(.+)$", stripped)
        if pair_match:
            if current_question and current_answer:
                questions.append({
                    "question": current_question,
                    "answer": " ".join(current_answer).strip(),
                })
            current_question = pair_match.group(1).strip()
            current_answer = [pair_match.group(2).strip()]
            continue

        if current_question:
            current_answer.append(stripped)

    if current_question and current_answer:
        questions.append({
            "question": current_question,
            "answer": " ".join(current_answer).strip(),
        })

    return questions


def normalize_tech_questions(raw: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if question:
            normalized.append({"question": question, "answer": answer})
    return normalized


def normalize_cbi_questions(raw: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        competency = str(item.get("competency", "")).strip()
        star_guide = str(item.get("star_guide", "")).strip()
        if question:
            normalized.append({
                "question": question,
                "competency": competency or "Behavioral",
                "star_guide": star_guide or (
                    "Situation: Set the context. Task: Your responsibility. "
                    "Action: Steps you took. Result: Outcome and impact."
                ),
            })
    return normalized
