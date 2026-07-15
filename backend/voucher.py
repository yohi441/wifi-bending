import secrets
from datetime import datetime

from sqlalchemy.orm import Session as DbSession

from backend.config import VOUCHER_ALPHABET, VOUCHER_CODE_LENGTH
from backend.models import Voucher


def generate_code() -> str:
    return "".join(secrets.choice(VOUCHER_ALPHABET) for _ in range(VOUCHER_CODE_LENGTH))


def generate_vouchers(
    db: DbSession,
    duration_minutes: int,
    price_pesos: float,
    count: int = 1,
) -> list[Voucher]:
    vouchers: list[Voucher] = []
    for _ in range(count):
        code = _unique_code(db)
        voucher = Voucher(
            code=code,
            duration_minutes=duration_minutes,
            price_pesos=price_pesos,
        )
        db.add(voucher)
        vouchers.append(voucher)
    db.commit()
    for v in vouchers:
        db.refresh(v)
    return vouchers


def _unique_code(db: DbSession) -> str:
    while True:
        code = generate_code()
        exists = db.query(Voucher).filter(Voucher.code == code).first()
        if not exists:
            return code


def validate_voucher(db: DbSession, code: str) -> Voucher | None:
    return db.query(Voucher).filter(
        Voucher.code == code.upper().strip(),
        Voucher.is_used == False,
        Voucher.is_active == True,
    ).first()


def mark_voucher_used(db: DbSession, code: str) -> Voucher | None:
    voucher = db.query(Voucher).filter(Voucher.code == code).first()
    if voucher:
        voucher.is_used = True
        voucher.used_at = datetime.utcnow()
        db.commit()
    return voucher


def deactivate_voucher(db: DbSession, voucher_id: int) -> Voucher | None:
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if voucher:
        voucher.is_active = False
        db.commit()
        db.refresh(voucher)
    return voucher


def get_vouchers(db: DbSession, skip: int = 0, limit: int = 100) -> list[Voucher]:
    return (
        db.query(Voucher)
        .order_by(Voucher.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_voucher_stats(db: DbSession) -> dict:
    total = db.query(Voucher).count()
    used = db.query(Voucher).filter(Voucher.is_used == True).count()
    active = db.query(Voucher).filter(Voucher.is_active == True).count()
    revenue = db.query(Voucher).filter(Voucher.is_used == True).with_entities(
        Voucher.price_pesos
    ).all()
    total_revenue = sum(r[0] for r in revenue if r[0] is not None)
    return {
        "total": total,
        "used": used,
        "unused": total - used,
        "active": active,
        "total_revenue": round(total_revenue, 2),
    }
