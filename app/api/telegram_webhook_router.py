from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram webhook updates."""
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
