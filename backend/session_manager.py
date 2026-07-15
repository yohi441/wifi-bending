from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DbSession

from backend.models import Session


def create_session(
    db: DbSession,
    mac_address: str,
    ip_address: str,
    duration_minutes: int,
    voucher_code: str | None = None,
) -> Session:
    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
    session = Session(
        voucher_code=voucher_code,
        mac_address=mac_address,
        ip_address=ip_address,
        duration_minutes=duration_minutes,
        end_time=end_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(db: DbSession, session_id: int) -> Session | None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if session:
        session.is_active = False
        session.end_time = datetime.utcnow()
        db.commit()
        db.refresh(session)
    return session


def get_active_session_by_mac(
    db: DbSession, mac_address: str
) -> Session | None:
    return db.query(Session).filter(
        Session.mac_address == mac_address,
        Session.is_active == True,
        Session.end_time > datetime.utcnow(),
    ).first()


def get_expired_sessions(db: DbSession) -> list[Session]:
    return db.query(Session).filter(
        Session.is_active == True,
        Session.end_time <= datetime.utcnow(),
    ).all()


def get_active_sessions(db: DbSession) -> list[Session]:
    return db.query(Session).filter(
        Session.is_active == True,
        Session.end_time > datetime.utcnow(),
    ).all()


def get_session_by_id(db: DbSession, session_id: int) -> Session | None:
    return db.query(Session).filter(Session.id == session_id).first()


def get_recent_sessions(
    db: DbSession, skip: int = 0, limit: int = 100
) -> list[Session]:
    return (
        db.query(Session)
        .order_by(Session.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_remaining_seconds(session: Session) -> int:
    if not session.end_time:
        return 0
    remaining = (session.end_time - datetime.utcnow()).total_seconds()
    return max(0, int(remaining))
