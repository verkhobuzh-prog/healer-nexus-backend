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

        # Спробувати передати в існуючий бот
        try:
            from app.telegram.healer_bot import process_update
            await process_update(data)
        except ImportError:
            # Якщо healer_bot не має process_update — спробувати admin_bot
            try:
                from app.telegram.admin_bot import process_update
                await process_update(data)
            except ImportError:
                logger.warning("No Telegram bot handler found. Webhook received but not processed.")

        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error("Telegram webhook error: %s", e)
        return JSONResponse(content={"ok": True})  # Завжди 200 для Telegram
