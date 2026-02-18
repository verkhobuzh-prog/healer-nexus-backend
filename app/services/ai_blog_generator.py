"""
AI blog draft generation using Gemini 2.5-flash with JSON output.
"""
from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Optional

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert blog writer. Output only valid JSON.
Use Markdown format with H2 and H3 headings only (no H1). Write in an empathetic, expert tone.
Content must be SEO-friendly and well-structured. Do not include code blocks or extra text around the JSON."""

GENERATION_PROMPT_TEMPLATE = """Write a blog post in {language} with this topic: {topic}
Tone: {tone}. Target length: about {word_count} words.

Practitioner context (use to personalize tone, do not invent facts):
- Name: {practitioner_name}
- Unique story: {unique_story}
- Specialties: {specialties}

Return a single JSON object with exactly these keys (no markdown wrapper):
- "title": string (SEO-friendly, in the requested language)
- "content": string (full markdown body, H2/H3 only)
- "meta_title": string (short for SEO, same language)
- "meta_description": string (1-2 sentences, same language)
"""


def _get_model():
    if not getattr(settings, "GEMINI_API_KEY", None) or not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    try:
        from google.generativeai.types import GenerationConfig
        return genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config=GenerationConfig(response_mime_type="application/json"),
        )
    except Exception:
        return genai.GenerativeModel("gemini-2.0-flash")


def _build_prompt(
    topic: str,
    word_count: int = 1000,
    language: str = "uk",
    tone: str = "empathetic_expert",
    practitioner_name: str = "",
    unique_story: Optional[str] = None,
    specialties: str = "",
) -> str:
    return GENERATION_PROMPT_TEMPLATE.format(
        topic=topic,
        word_count=word_count,
        language=language,
        tone=tone,
        practitioner_name=practitioner_name or "Author",
        unique_story=unique_story or "Not specified",
        specialties=specialties or "General",
    )


async def generate_blog_draft(
    topic: str,
    word_count: int = 1000,
    language: str = "uk",
    tone: str = "empathetic_expert",
    practitioner_name: str = "",
    unique_story: Optional[str] = None,
    specialties: Optional[str] = None,
) -> dict[str, Any]:
    """
    Returns dict with keys: title, content, meta_title, meta_description.
    On JSON parse error, returns raw text as content and None for structured fields.
    """
    prompt = _build_prompt(
        topic=topic,
        word_count=word_count,
        language=language,
        tone=tone,
        practitioner_name=practitioner_name or "",
        unique_story=unique_story,
        specialties=specialties or "",
    )
    full = f"{SYSTEM_PROMPT}\n\n{prompt}"
    text = ""
    try:
        model = _get_model()
        response = await asyncio.to_thread(model.generate_content, full)
        text = (response.text or "").strip()
        if not text:
            return {"title": topic[:200], "content": "", "meta_title": None, "meta_description": None}
        # Strip markdown code block if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        data = json.loads(text)
        return {
            "title": data.get("title") or topic[:200],
            "content": data.get("content") or "",
            "meta_title": data.get("meta_title"),
            "meta_description": data.get("meta_description"),
        }
    except json.JSONDecodeError as e:
        logger.warning("AI blog JSON parse error, using raw text: %s", e)
        return {
            "title": topic[:200],
            "content": text,
            "meta_title": None,
            "meta_description": None,
        }
    except Exception as e:
        logger.exception("AI blog generation failed: %s", e)
        return {
            "title": topic[:200],
            "content": "",
            "meta_title": None,
            "meta_description": None,
        }
