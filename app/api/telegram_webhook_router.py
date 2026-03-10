import logging
import os

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])

TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    """Receive Telegram webhook updates."""
    if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Telegram webhook: invalid secret token")
        return JSONResponse(content={"ok": False}, status_code=403)
    try:
        data = await request.json()
        logger.info("Telegram webhook received: %s", data.get("update_id", "unknown"))

        try:
            from app.telegram.healer_bot import process_update
            await process_update(data)
        except Exception as e:
            logger.exception("process_update error: %s", e)

        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.exception("Telegram webhook error: %s", e)
        return JSONResponse(content={"ok": True})  # Завжди 200 для Telegram
