from datetime import datetime

from pydantic import BaseModel, Field


class VoucherCreate(BaseModel):
    duration_minutes: int = Field(ge=1, le=43200)
    price_pesos: float = Field(ge=0.0)
    count: int = Field(default=1, ge=1, le=100)


class VoucherResponse(BaseModel):
    id: int
    code: str
    duration_minutes: int
    price_pesos: float
    is_used: bool
    is_active: bool
    created_at: datetime
    used_at: datetime | None = None


class VoucherRedeem(BaseModel):
    code: str
    mac_address: str = Field(pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    ip_address: str


class SessionResponse(BaseModel):
    id: int
    voucher_code: str | None
    mac_address: str
    ip_address: str
    start_time: datetime
    end_time: datetime | None
    duration_minutes: int
    is_active: bool
    data_used_bytes: int
    remaining_seconds: int | None = None


class StatusResponse(BaseModel):
    authenticated: bool
    session: SessionResponse | None = None
    message: str = ""


class CoinStatusResponse(BaseModel):
    amount: int
    minutes: int
    safe: bool
    button_enabled: bool
    auto_grant_seconds: int
    rate: int


class CoinPulseRequest(BaseModel):
    amount: int = Field(ge=1, le=1000)


class CoinSettingsUpdate(BaseModel):
    minutes_per_peso: int = Field(ge=1, le=60)
    auto_grant_timeout: int = Field(ge=3, le=60)
    minimum_amount: int = Field(ge=1, le=100)
