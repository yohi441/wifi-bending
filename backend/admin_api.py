from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from backend.auth import require_admin, verify_password
from backend.database import get_db
from backend.firewall import revoke_access
from backend.models import Admin, Setting
from backend.schemas import CoinSettingsUpdate, LoginRequest, SessionResponse, VoucherCreate, VoucherResponse
from backend.session_manager import (
    end_session,
    get_active_sessions,
    get_recent_sessions,
    get_session_by_id,
)
from backend.voucher import (
    deactivate_voucher,
    generate_vouchers,
    get_voucher_stats,
    get_vouchers,
)

from backend.utils import ph_time

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="backend/templates")
templates.env.filters["ph_time"] = ph_time


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "admin/login.html", {"error": error})


@router.post("/login")
def admin_login(
    username: str = Form(...),
    password: str = Form(...),
    request: Request = None,
    db: DbSession = Depends(get_db),
):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            request, "admin/login.html",
            {"error": "Invalid username or password"},
        )
    request.session["admin_id"] = admin.id
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: DbSession = Depends(get_db)):
    require_admin(request)
    stats = get_voucher_stats(db)
    active = get_active_sessions(db)
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "stats": stats,
            "active_sessions_count": len(active),
        },
    )


@router.get("/vouchers", response_class=HTMLResponse)
def admin_vouchers(
    request: Request,
    page: int = Query(1, ge=1),
    db: DbSession = Depends(get_db),
):
    require_admin(request)
    limit = 50
    skip = (page - 1) * limit
    vouchers = get_vouchers(db, skip=skip, limit=limit)
    stats = get_voucher_stats(db)
    return templates.TemplateResponse(
        request,
        "admin/vouchers.html",
        {
            "vouchers": vouchers,
            "stats": stats,
            "page": page,
        },
    )


@router.get("/vouchers/create", response_class=HTMLResponse)
def admin_create_voucher_page(request: Request):
    require_admin(request)
    return templates.TemplateResponse(
        request,
        "admin/create_voucher.html",
    )


@router.post("/vouchers/create")
def admin_create_voucher(
    data: VoucherCreate,
    request: Request,
    db: DbSession = Depends(get_db),
):
    require_admin(request)
    vouchers = generate_vouchers(
        db=db,
        duration_minutes=data.duration_minutes,
        price_pesos=data.price_pesos,
        count=data.count,
    )
    return {
        "success": True,
        "vouchers": [
            {
                "id": v.id,
                "code": v.code,
                "duration_minutes": v.duration_minutes,
                "price_pesos": v.price_pesos,
            }
            for v in vouchers
        ],
    }


@router.post("/vouchers/{voucher_id}/deactivate")
def admin_deactivate_voucher(
    voucher_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
):
    require_admin(request)
    voucher = deactivate_voucher(db, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return {"success": True}


@router.get("/sessions", response_class=HTMLResponse)
def admin_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    db: DbSession = Depends(get_db),
):
    require_admin(request)
    limit = 50
    skip = (page - 1) * limit
    sessions = get_recent_sessions(db, skip=skip, limit=limit)
    active = get_active_sessions(db)
    return templates.TemplateResponse(
        request,
        "admin/sessions.html",
        {
            "sessions": sessions,
            "active_sessions": active,
            "page": page,
        },
    )


@router.post("/sessions/{session_id}/disconnect")
def admin_disconnect_session(
    session_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
):
    require_admin(request)
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    revoke_access(session.mac_address)
    end_session(db, session_id)
    return {"success": True}


@router.get("/settings", response_class=HTMLResponse)
def admin_settings_page(request: Request, db: DbSession = Depends(get_db)):
    require_admin(request)
    def get_val(key: str, default: str) -> int:
        row = db.query(Setting).filter(Setting.key == key).first()
        return int(row.value) if row else int(default)

    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {
            "minutes_per_peso": get_val("coin_minutes_per_peso", "6"),
            "auto_grant_timeout": get_val("coin_auto_grant_timeout", "10"),
            "minimum_amount": get_val("coin_minimum_amount", "1"),
        },
    )


@router.post("/settings")
def admin_update_settings(
    data: CoinSettingsUpdate,
    request: Request,
    db: DbSession = Depends(get_db),
):
    require_admin(request)
    def upsert(key: str, value: str):
        row = db.query(Setting).filter(Setting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))

    upsert("coin_minutes_per_peso", str(data.minutes_per_peso))
    upsert("coin_auto_grant_timeout", str(data.auto_grant_timeout))
    upsert("coin_minimum_amount", str(data.minimum_amount))
    db.commit()
    return {"success": True}
