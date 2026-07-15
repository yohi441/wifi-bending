import logging

from sqlalchemy.orm import Session as DbSession

from backend.coin_state import CoinState
from backend.database import SessionLocal
from backend.firewall import get_mac_from_ip, grant_access
from backend.models import Setting
from backend.session_manager import create_session as create_db_session
from backend.session_manager import get_active_session_by_mac
from backend.voucher import generate_vouchers

logger = logging.getLogger(__name__)

coin_state = CoinState()


def _get_settings(db: DbSession) -> tuple[int, int, int]:
    def get_val(key: str, default: str) -> int:
        row = db.query(Setting).filter(Setting.key == key).first()
        return int(row.value) if row else int(default)

    return (
        get_val("coin_minutes_per_peso", "6"),
        get_val("coin_auto_grant_timeout", "10"),
        get_val("coin_minimum_amount", "1"),
    )


def process_coin(
    amount: int,
    mac_address: str,
    ip_address: str,
    db: DbSession | None = None,
) -> dict:
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        minutes_per_peso, auto_grant_timeout, minimum_amount = _get_settings(db)
        duration_minutes = amount * minutes_per_peso

        if duration_minutes < 1:
            return {"success": False, "message": "Amount too low"}

        existing = get_active_session_by_mac(db, mac_address)
        if existing:
            return {"success": False, "message": "Already have an active session"}

        vouchers = generate_vouchers(
            db=db,
            duration_minutes=duration_minutes,
            price_pesos=float(amount),
            count=1,
        )
        voucher = vouchers[0]

        grant_access(mac_address)
        session = create_db_session(
            db=db,
            mac_address=mac_address,
            ip_address=ip_address,
            duration_minutes=duration_minutes,
            voucher_code=voucher.code,
        )

        coin_state.reset()

        logger.info(
            "Coin op: ₱%d → %d min, voucher %s, session %d",
            amount, duration_minutes, voucher.code, session.id,
        )

        return {
            "success": True,
            "message": f"Access granted for {duration_minutes} minutes",
            "session_id": session.id,
            "duration_minutes": duration_minutes,
            "voucher_code": voucher.code,
        }
    finally:
        if close_db:
            db.close()
