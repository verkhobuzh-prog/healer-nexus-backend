"""
Telegram auto-post for blog publications. Sends announcements to practitioner channel.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.config import settings

logger = logging.getLogger(__name__)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"!\[.*?\]\(.+?\)", "", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _tag_to_hashtag(tag: str) -> str:
    try:
        from app.services.blog_slug import generate_slug
        slug = generate_slug(tag)
        return re.sub(r"[^a-zA-Z0-9]", "", slug)
    except ImportError:
        return re.sub(r"[^a-zA-Z0-9]", "", tag)


class BlogTelegramService:
    def __init__(self) -> None:
        self._bot: Optional[Bot] = None

    def _get_bot(self) -> Bot:
        if not self._bot:
            token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured")
            self._bot = Bot(token=token)
        return self._bot

    async def send_post_announcement(
        self,
        channel_id: str,
        title: str,
        excerpt: str,
        post_url: str,
        reading_time: int,
        tags: Optional[list[str]] = None,
        featured_image_url: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> bool:
        try:
            bot = self._get_bot()
            text = self._format_message(
                title=title,
                excerpt=excerpt,
                post_url=post_url,
                reading_time=reading_time,
                tags=tags,
                author_name=author_name,
            )
            if len(text) > 1024:
                text = text[:1021] + "..."
            if featured_image_url:
                try:
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=featured_image_url,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                    )
                except TelegramError as img_err:
                    logger.warning("Failed to send photo, fallback to text: %s", img_err)
                    await bot.send_message(
                        chat_id=channel_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=False,
                    )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
            logger.info("Blog announcement sent to %s: %s", channel_id, title)
            return True
        except ValueError as e:
            logger.error("Telegram config error: %s", e)
            return False
        except TelegramError as e:
            logger.error("Telegram send error to %s: %s", channel_id, e)
            return False
        except Exception as e:
            logger.error("Unexpected error sending to Telegram: %s", e, exc_info=True)
            return False

    @staticmethod
    def _format_message(
        title: str,
        excerpt: str,
        post_url: str,
        reading_time: int,
        tags: Optional[list[str]] = None,
        author_name: Optional[str] = None,
    ) -> str:
        lines = ["📝 <b>Нова стаття</b>", "", f"<b>{_escape_html(title)}</b>", ""]
        clean_excerpt = _strip_markdown(excerpt)[:200]
        if len(excerpt) > 200:
            clean_excerpt = clean_excerpt.rsplit(" ", 1)[0] + "..."
        lines.append(_escape_html(clean_excerpt))
        lines.append("")
        meta_parts = [f"⏱ {reading_time} хв читання"]
        if tags:
            hashtags = " ".join(f"#{_tag_to_hashtag(t)}" for t in tags[:5])
            meta_parts.append(f"🏷 {hashtags}")
        lines.append(" | ".join(meta_parts))
        lines.append("")
        if author_name:
            lines.append(f"✍️ {_escape_html(author_name)}")
        lines.append(f'👉 <a href="{post_url}">Читати повністю</a>')
        return "\n".join(lines)


blog_telegram_service = BlogTelegramService()
