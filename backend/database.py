from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import backend.models
    from backend.config import DEFAULT_COIN_SETTINGS
    from backend.auth import hash_password

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for key, value in DEFAULT_COIN_SETTINGS.items():
            existing = db.query(backend.models.Setting).filter(
                backend.models.Setting.key == key
            ).first()
            if not existing:
                db.add(backend.models.Setting(key=key, value=value))

        existing_admin = db.query(backend.models.Admin).filter(
            backend.models.Admin.username == "admin"
        ).first()
        if not existing_admin:
            db.add(backend.models.Admin(
                username="admin",
                password_hash=hash_password("admin123"),
            ))
        db.commit()
    finally:
        db.close()
