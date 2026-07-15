import asyncio
import logging

from backend.config import SESSION_CHECK_INTERVAL
from backend.database import SessionLocal
from backend.firewall import revoke_access
from backend.session_manager import end_session, get_expired_sessions

logger = logging.getLogger(__name__)

_stop_event = asyncio.Event()


def stop():
    _stop_event.set()


async def session_expiry_loop() -> None:
    while not _stop_event.is_set():
        try:
            await asyncio.to_thread(_expire_sessions)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Session expiry check failed: %s", e)
        try:
            await asyncio.wait_for(
                _stop_event.wait(), timeout=SESSION_CHECK_INTERVAL
            )
        except asyncio.TimeoutError:
            pass


def _expire_sessions() -> None:
    db = SessionLocal()
    try:
        expired = get_expired_sessions(db)
        for session in expired:
            revoke_access(session.mac_address)
            end_session(db, session.id)
            logger.info(
                "Expired session %d for %s",
                session.id,
                session.mac_address,
            )
    finally:
        db.close()
