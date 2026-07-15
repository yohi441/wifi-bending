from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from backend.database import get_db
from backend.firewall import get_mac_from_ip, grant_access
from pydantic import BaseModel

from backend.session_manager import (
    create_session,
    get_active_session_by_mac,
    get_remaining_seconds,
)
from backend.voucher import mark_voucher_used, validate_voucher

from backend.coin_acceptor import coin_state, process_coin
from backend.config import COIN_POLL_INTERVAL
from backend.models import Setting
from backend.schemas import CoinPulseRequest, CoinStatusResponse, StatusResponse
from backend.utils import ph_time

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")
templates.env.filters["ph_time"] = ph_time


class RedeemRequest(BaseModel):
    code: str


@router.get("/generate_204")
@router.get("/hotspot-detect.html")
@router.get("/ncsi.txt")
@router.get("/connecttest.txt")
@router.get("/success.txt")
def captive_detection(request: Request, db: DbSession = Depends(get_db)):
    mac = get_mac_from_ip(request.client.host) if request.client else None
    if mac:
        session = get_active_session_by_mac(db, mac)
        if session:
            return Response(status_code=204)
    return HTMLResponse(
        status_code=302,
        content="",
        headers={"Location": "/portal"},
    )


@router.get("/portal", response_class=HTMLResponse)
def portal_page(request: Request, db: DbSession = Depends(get_db)):
    mac = get_mac_from_ip(request.client.host) if request.client else None
    if mac:
        session = get_active_session_by_mac(db, mac)
        if session:
            remaining = get_remaining_seconds(session)
            return templates.TemplateResponse(
                request,
                "success.html",
                {
                    "remaining_seconds": remaining,
                    "remaining_minutes": remaining // 60,
                    "mac": mac,
                },
            )
    return templates.TemplateResponse(
        request,
        "portal.html",
        {
            "error": "",
            "default_tab": "coin",
            "COIN_POLL_INTERVAL": COIN_POLL_INTERVAL,
        },
    )


@router.get("/status", response_model=StatusResponse)
def check_status(request: Request, db: DbSession = Depends(get_db)):
    mac = get_mac_from_ip(request.client.host) if request.client else None
    if not mac:
        return StatusResponse(
            authenticated=False,
            message="Could not determine MAC address",
        )
    session = get_active_session_by_mac(db, mac)
    if session:
        remaining = get_remaining_seconds(session)
        return StatusResponse(
            authenticated=True,
            message="Session active",
        )
    return StatusResponse(
        authenticated=False,
        message="No active session",
    )


@router.post("/redeem")
def redeem_voucher(
    request: Request,
    data: RedeemRequest,
    db: DbSession = Depends(get_db),
):
    voucher = validate_voucher(db, data.code)
    if not voucher:
        return {"success": False, "message": "Invalid or expired voucher code"}

    ip_address = request.client.host if request.client else "0.0.0.0"
    mac_address = get_mac_from_ip(ip_address)

    if not mac_address:
        return {"success": False, "message": "Could not identify your device"}

    existing = get_active_session_by_mac(db, mac_address)
    if existing:
        return {"success": False, "message": "Already have an active session"}

    grant_access(mac_address)
    session = create_session(
        db=db,
        mac_address=mac_address,
        ip_address=ip_address,
        duration_minutes=voucher.duration_minutes,
        voucher_code=voucher.code,
    )
    mark_voucher_used(db, voucher.code)

    return {
        "success": True,
        "message": f"Access granted for {voucher.duration_minutes} minutes",
        "session_id": session.id,
        "duration_minutes": voucher.duration_minutes,
    }


@router.get("/coin-status")
def coin_status(request: Request, db: DbSession = Depends(get_db)):
    def get_val(key: str, default: str) -> int:
        row = db.query(Setting).filter(Setting.key == key).first()
        return int(row.value) if row else int(default)

    rate = get_val("coin_minutes_per_peso", "6")
    timeout = get_val("coin_auto_grant_timeout", "10")
    minimum = get_val("coin_minimum_amount", "1")

    return coin_state.to_dict(rate, timeout, minimum)


@router.post("/coin-pulse")
def coin_pulse(
    data: CoinPulseRequest,
):
    coin_state.add_coin(data.amount)
    return {"success": True, "total_amount": coin_state.amount}


@router.post("/coin-connect")
def coin_connect(
    request: Request,
    db: DbSession = Depends(get_db),
):
    if coin_state.amount < 1:
        return {"success": False, "message": "Insert coin first"}

    ip_address = request.client.host if request.client else "0.0.0.0"
    mac_address = get_mac_from_ip(ip_address)

    if not mac_address:
        return {"success": False, "message": "Could not identify your device"}

    result = process_coin(
        amount=coin_state.amount,
        mac_address=mac_address,
        ip_address=ip_address,
        db=db,
    )
    return result
