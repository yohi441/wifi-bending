# Piso WiFi — Developer Documentation

> **Target audience:** Django developers new to FastAPI.
> Every concept is explained with its Django equivalent first.

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [Django → FastAPI Translation Table](#2-django--fastapi-translation-table)
3. [Project Map](#3-project-map)
4. [How a Request Flows Through the Server](#4-how-a-request-flows-through-the-server)
5. [Entry Point — `backend/main.py`](#5-entry-point--backendmainpy)
6. [Configuration — `backend/config.py`](#6-configuration--backendconfigpy)
7. [Database — `backend/database.py` + `models.py`](#7-database--backenddatabasepy--modelspy)
8. [Routes — `backend/captive_portal.py`](#8-routes--backendcaptive_portalpy)
9. [Admin Routes — `backend/admin_api.py`](#9-admin-routes--backendadmin_apipy)
10. [Voucher System — `backend/voucher.py`](#10-voucher-system--backendvoucherpy)
11. [Session Manager — `backend/session_manager.py`](#11-session-manager--backendsession_managerpy)
12. [Coin System — Full Flow](#12-coin-system--full-flow)
13. [Scheduler — `backend/scheduler.py`](#13-scheduler--backendschedulerpy)
14. [Firewall — `backend/firewall.py`](#14-firewall--backendfirewallpy)
15. [Templates (Jinja2 + Alpine.js)](#15-templates-jinja2--alpinejs)
16. [Static JS — `portal.js` and `success.js`](#16-static-js--portaljs-and-successjs)
17. [Common Pitfalls for Django Devs](#17-common-pitfalls-for-django-devs)
18. [Running & Testing](#18-running--testing)
19. [Deploying on Raspberry Pi](#19-deploying-on-raspberry-pi)

---

## 1. What Is This?

Piso WiFi is a **captive portal** system for coin-operated WiFi. Users insert coins at a vending machine, the portal detects the pulses, grants internet access, and starts a timed session. Vouchers can also be sold manually.

**High-level architecture:**

```
Browser ──▶ FastAPI ──▶ SQLite (via SQLAlchemy)
                │
                ├── Jinja2 templates (server-rendered HTML)
                ├── Alpine.js (interactive frontend)
                └── iptables (network access control on Pi)
```

**Key facts:**
- FastAPI serves both the HTML pages (portal + admin) and JSON API endpoints
- SQLite database with SQLAlchemy ORM (no migrations — tables auto-created)
- Dev mode (`DEV_MODE=true`) simulates everything without real coin hardware or iptables
- All timestamps in admin are displayed in **Asia/Manila** timezone
- No authentication on admin pages (add your own if deploying publicly)

---

## 2. Django → FastAPI Translation Table

| Django Concept | FastAPI Equivalent | Where in this project |
|---|---|---|
| `views.py` | Route functions in a router file | `captive_portal.py`, `admin_api.py` |
| `urls.py` (urlpatterns) | `@router.get()` / `@router.post()` decorators | Each route file has a `router = APIRouter()` |
| `include()` in urls | `app.include_router(router)` | `main.py:47-48` |
| `request.POST`, `request.GET` | Pydantic model + `Depends()` | `schemas.py` defines the shape, routes use `data: MyModel` |
| `request.user` | `Depends()` for auth (not in this project) | N/A — no auth yet |
| `@login_required` | Custom `Depends()` function | N/A in this project |
| `manage.py runserver` | `python -m backend.main` | Runs uvicorn directly |
| Django ORM (`MyModel.objects.filter()`) | SQLAlchemy (`db.query(MyModel).filter().first()`) | Every route that needs DB access |
| `python manage.py shell` | `./venv/bin/python` | Import modules manually |
| `settings.py` | `backend/config.py` | Plain Python constants with `os.getenv()` |
| `{% url "name" arg %}` | `request.url_for("endpoint_name")` | Rarely used — hardcoded paths in templates |
| `{{ csrf_token }}` | Not used | No CSRF — this is an internal appliance, not a public web app |
| `HttpResponse()` / `render()` | `HTMLResponse` / `TemplateResponse(request, name, context)` | The context dict works identically to Django |
| `JsonResponse({})` | `return {"key": "value"}` | FastAPI auto-serializes dicts to JSON |
| `@api_view` decorator | `@router.get(...)`, `@router.post(...)` | With path, response_model, etc. |
| Middleware (process_request) | Lifespan events + `@app.exception_handler` | `main.py:28-40` |
| `python manage.py migrate` | `init_db()` at startup | Auto-creates tables + seeds defaults |
| `request.session` | Not used | Sessions are stored in DB, not cookies |
| `{% include %}` | Same (`{% include %}`) | Jinja2 is essentially identical to Django templates |
| `django.db.models.DateTimeField` | `mapped_column(DateTime)` | With `default=datetime.utcnow` |
| `django.db.models.ForeignKey` | `mapped_column(Integer, ForeignKey(...))` | Not used in this project (simple schema) |
| `@transaction.atomic` | `db.commit()` / `db.rollback()` | Auto-commit pattern |
| Form handling (Django Forms) | Pydantic models + Alpine.js forms | Forms are HTML with `x-model` bindings |

---

## 3. Project Map

```
piso_wifi/
├── DOCS.md                          ← This file
├── README.md
├── backend/
│   ├── __init__.py
│   ├── main.py                      ← Entry point (like Django's manage.py + wsgi.py combined)
│   ├── config.py                    ← All settings (like Django's settings.py)
│   ├── database.py                  ← SQLAlchemy engine + session + init_db()
│   ├── models.py                    ← ORM models (Voucher, Session, Setting)
│   ├── schemas.py                   ← Pydantic models (request/response validation)
│   ├── captive_portal.py            ← Portal routes (/portal, /redeem, /coin-*, /status)
│   ├── admin_api.py                 ← Admin routes (/admin/*)
│   ├── voucher.py                   ← Voucher CRUD + stats
│   ├── session_manager.py           ← Session CRUD + expiry queries
│   ├── coin_state.py                ← In-memory coin insertion state (thread-safe singleton)
│   ├── coin_acceptor.py             ← Coin → voucher → session pipeline
│   ├── scheduler.py                 ← Background session expiry loop
│   ├── firewall.py                  ← iptables management + MAC resolution
│   ├── utils.py                     ← PH timezone filter for Jinja2
│   ├── static/
│   │   ├── portal.js                ← Alpine component for portal page
│   │   └── success.js               ← Alpine component for success page
│   └── templates/
│       ├── portal.html              ← Captive portal page (coin + voucher tabs)
│       ├── success.html             ← "Connected" page with countdown
│       └── admin/
│           ├── base.html            ← Admin layout (sidebar, responsive)
│           ├── dashboard.html       ← Stats overview
│           ├── vouchers.html        ← Voucher list with pagination
│           ├── create_voucher.html  ← Create new vouchers
│           ├── sessions.html        ← Active + recent sessions
│           └── settings.html        ← Coin rate settings
├── scripts/
│   ├── setup_pi.sh                  ← Raspberry Pi setup script
│   └── coin-simulator.py            ← CLI tool to simulate coin pulses
└── requirements.txt
```

---

## 4. How a Request Flows Through the Server

Here's what happens step-by-step when you visit `http://localhost:8000/portal`:

### A. Startup (one-time)

```
python -m backend.main
  │
  ├── create_app() is called
  │     ├── FastAPI() instance created
  │     ├── Static files mounted at /static
  │     ├── Portal router included (/portal, /redeem, etc.)
  │     ├── Admin router included (/admin/*)
  │     └── Root redirect (/) and 404 handler registered
  │
  └── lifespan context manager starts
        ├── init_db() creates tables + seeds settings
        └── session_expiry_loop() starts as background task
```

**Django analogy:** `create_app()` is like `settings.py` + `urls.py` combined. The `lifespan` is like Django's `AppConfig.ready()` method — code that runs at startup and shutdown.

### B. Request arrives

```
1. uvicorn receives HTTP GET /portal
     │
2. FastAPI matches the path → @router.get("/portal") in captive_portal.py
     │
3. Dependency injection runs: Depends(get_db)
     ├── get_db() creates a new SQLAlchemy session
     └── sessions are auto-closed when the request ends
     │
4. Route handler executes: portal_page(request, db)
     ├── Gets client IP from request.client.host
     ├── Resolves MAC address from IP (or synthetic in dev mode)
     ├── Checks if there's an active session for that MAC
     └── Returns either:
         ├── success.html (if session exists)
         └── portal.html (if no session)
     │
5. Jinja2 renders the template with the context dict
     │
6. FastAPI returns HTMLResponse to the browser
```

**Django analogy:**
- `@router.get(...)` = `@api_view(["GET"])` + `path("portal/", view)`
- `Depends(get_db)` = middleware that opens/closes DB connection per request
- `TemplateResponse(request, "template.html", {"key": val})` = `render(request, "template.html", {"key": val})`

### C. What makes FastAPI different from Django at the framework level

| Aspect | Django | FastAPI |
|---|---|---|
| Request handling | WSGI (synchronous) | ASGI (async by default, but sync works too) |
| URL routing | Separate `urls.py` files | Decorators on functions |
| Validation | Forms / DRF serializers | Pydantic (automatic, generates OpenAPI docs) |
| DB session | Per-request middleware (or DRF) | Explicit `Depends(get_db)` in each route |
| Startup code | `AppConfig.ready()` | `lifespan` context manager |
| ORM | Django ORM (auto-managed) | SQLAlchemy (explicit sessions) |
| Admin | django.contrib.admin | Custom-built (just HTML pages) |

---

## 5. Entry Point — `backend/main.py`

This file does three jobs that Django splits across `manage.py`, `wsgi.py`, and `settings.py`.

### 5.1 Creating the app

```python
def create_app() -> FastAPI:
    app = FastAPI(title="Piso WiFi", version="1.0.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="backend/static"), name="static")
    app.include_router(portal_router)
    app.include_router(admin_router)
    return app
```

- `FastAPI(...)` — like `django.setup()` + creating the WSGI application
- `app.mount("/static", ...)` — serves files from `backend/static/` at `/static/...` (like `django.contrib.staticfiles`)
- `app.include_router(...)` — like including a `urls.py` file

**Note:** The portal router is included at `/` (no prefix), while the admin router is included at `/admin` (prefix set inside `admin_api.py`).

### 5.2 Lifespan (startup / shutdown)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()                          # Create tables + seed defaults
    _scheduler_task = asyncio.create_task(session_expiry_loop())  # Start background loop
    yield                               # App is now running
    stop_scheduler()                    # Signal background loop to stop
    _scheduler_task.cancel()            # Wait for it to finish
```

**Django analogy:** Put `init_db()` in `AppConfig.ready()` and the background loop in a management command. The `yield` splits "before server starts" from "after server stops".

### 5.3 Custom server + signal handling

```python
class _Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass                           # Don't let uvicorn install its own handlers

def main():
    server = _Server(config)
    loop.add_signal_handler(signal.SIGINT, lambda: os._exit(0))
    loop.run_until_complete(server.serve())
```

**Why this exists:** When you press Ctrl+C, uvicorn's default graceful shutdown hangs waiting for connections to close. This setup bypasses uvicorn's signals and kills the process immediately with `os._exit(0)`. This is fine for a local appliance that runs in a terminal.

### 5.4 How to run it

```bash
# From the project root:
./venv/bin/python -m backend.main

# Or directly:
python -m backend.main

# The server starts on http://0.0.0.0:8000
```

**Django comparison:** `python manage.py runserver` has auto-reload, debug toolbar, etc. This is just uvicorn — no auto-reload (add `--reload` if you want it).

---

## 6. Configuration — `backend/config.py`

All settings are plain Python variables. No `settings.py` module discovery, no `os.environ` wrappers — just direct assignments with `os.getenv()` fallbacks.

```python
DATABASE_URL = f"sqlite:///{BASE_DIR}/piso_wifi.db"   # File location for SQLite
HOST = os.getenv("HOST", "0.0.0.0")                   # Listen on all interfaces
PORT = int(os.getenv("PORT", "8000"))
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"  # Dev mode on by default
```

**Key settings you might change:**

| Variable | Default | What it controls |
|---|---|---|
| `DEV_MODE` | `true` | When true: synthetic MACs, no iptables, no real hardware |
| `COIN_MINUTES_PER_PESO` | `6` | How many minutes ₱1 buys |
| `COIN_AUTO_GRANT_TIMEOUT` | `10` | Seconds of inactivity before auto-connect |
| `COIN_MINIMUM_AMOUNT` | `1` | Minimum peso amount to enable the Connect button |
| `COIN_POLL_INTERVAL` | `2` | Seconds between portal polls to `/coin-status` |
| `SESSION_CHECK_INTERVAL` | `15` | Seconds between background session expiry checks |
| `VOUCHER_ALPHABET` | `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` | Characters used in voucher codes (no 0/O/1/I/L) |

**Django comparison:** Instead of `from django.conf import settings`, you do `from backend.config import COIN_MINUTES_PER_PESO`.

---

## 7. Database — `backend/database.py` + `models.py`

### 7.1 Engine and Session

```python
# database.py
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

- `engine` — the connection pool (like Django's `DATABASES` configuration)
- `SessionLocal` — a factory that creates new DB sessions (like Django's `db.session`)

The `connect_args={"check_same_thread": False}` is SQLite-specific. It allows SQLAlchemy to pass the connection between threads (necessary because FastAPI runs sync routes in a thread pool).

### 7.2 The `get_db()` dependency

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This is a **generator function** used as a FastAPI dependency. Every route that needs the database declares `db: DbSession = Depends(get_db)` in its parameters. FastAPI calls `get_db()`, gets a session, passes it to the route, and closes it when the response is sent.

**Django analogy:** This replaces Django's per-request middleware that opens/closes the DB connection.

**How to use it in a route:**
```python
@router.get("/example")
def my_route(db: DbSession = Depends(get_db)):
    vouchers = db.query(Voucher).all()  # Same as Voucher.objects.all()
    return {"count": len(vouchers)}
```

### 7.3 `init_db()` — like migrations

```python
def init_db():
    Base.metadata.create_all(bind=engine)     # CREATE TABLE IF NOT EXISTS
    # Seed default settings if they don't exist
    for key, value in DEFAULT_COIN_SETTINGS.items():
        if not db.query(Setting).filter(Setting.key == key).first():
            db.add(Setting(key=key, value=value))
```

**Django analogy:** This is both `manage.py makemigrations` + `manage.py migrate` + loading initial data fixtures. It runs at every startup and is idempotent (safe to run multiple times).

**Important:** There are no migration files. If you change a model, you must either:
- Delete `piso_wifi.db` and restart (loses data)
- Add `ALTER TABLE` SQL manually via `db.execute()`

For production, you'd want Alembic (like Django's migration framework).

### 7.4 Models

```python
class Voucher(Base):
    __tablename__ = "vouchers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price_pesos: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**Django analogy:**
- `class Voucher(Base)` → `class Voucher(models.Model)`
- `Mapped[int]` → implicit in Django
- `mapped_column(Integer, primary_key=True)` → `models.AutoField(primary_key=True)`
- `mapped_column(String(20), unique=True)` → `models.CharField(max_length=20, unique=True)`
- `mapped_column(Boolean, default=False)` → `models.BooleanField(default=False)`
- `Mapped[datetime | None]` → `models.DateTimeField(null=True, blank=True)`

**Models in this project:**

| Model | Table | Purpose |
|---|---|---|
| `Voucher` | `vouchers` | Pre-generated or coin-generated access codes |
| `Session` | `sessions` | Active/recent internet sessions (MAC + timer) |
| `Setting` | `settings` | Key-value store for coin rate, timeout, minimum |

### 7.5 Query patterns

```python
# All records
db.query(Voucher).all()                    # Voucher.objects.all()

# Filtered
db.query(Voucher).filter(Voucher.is_used == False).all()
                                           # Voucher.objects.filter(is_used=False)

# First match
db.query(Voucher).filter(Voucher.code == code).first()
                                           # Voucher.objects.filter(code=code).first()

# Count
db.query(Voucher).count()                  # Voucher.objects.count()

# Order by
db.query(Voucher).order_by(Voucher.created_at.desc()).all()
                                           # Voucher.objects.order_by('-created_at')

# Limit/offset (pagination)
db.query(Voucher).offset(0).limit(50).all()
                                           # Voucher.objects.all()[0:50]

# Create
db.add(Voucher(code="ABC", duration_minutes=30))
db.commit()
db.refresh(voucher)                         # Refresh to get auto-generated fields
                                           # Equivalent to: voucher = Voucher.objects.create(...)

# Update
voucher = db.query(Voucher).filter(Voucher.id == 1).first()
voucher.is_used = True
db.commit()
                                           # Equivalent to: Voucher.objects.filter(id=1).update(is_used=True)

# Delete
db.delete(voucher)
db.commit()
                                           # Equivalent to: voucher.delete()
```

---

## 8. Routes — `backend/captive_portal.py`

This file handles the **captive portal** — what users see when they first connect to the WiFi. It's the most important route file.

### 8.1 Router setup

```python
router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")
templates.env.filters["ph_time"] = ph_time
```

- `router = APIRouter()` — like creating a `urlpatterns` list. Later registered in `main.py:47`
- `Jinja2Templates(...)` — the template engine. Configured once here with the PH timezone filter
- The `ph_time` filter converts UTC timestamps to Asia/Manila in templates

### 8.2 Route table

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/generate_204` | `captive_detection` | Android/iOS captive portal detection |
| GET | `/hotspot-detect.html` | (same handler) | Apple captive portal detection |
| GET | `/ncsi.txt` | (same handler) | Windows captive portal detection |
| GET | `/connecttest.txt` | (same handler) | Other captive portal detection |
| GET | `/success.txt` | (same handler) | Other captive portal detection |
| GET | `/portal` | `portal_page` | Main portal or success page |
| GET | `/status` | `check_status` | JSON: is the client authenticated? |
| POST | `/redeem` | `redeem_voucher` | Redeem a voucher code |
| GET | `/coin-status` | `coin_status` | JSON: current coin state |
| POST | `/coin-pulse` | `coin_pulse` | Register a coin pulse |
| POST | `/coin-connect` | `coin_connect` | Convert coins to session |

### 8.3 Captive portal detection endpoints

```python
@router.get("/generate_204")
@router.get("/hotspot-detect.html")
@router.get("/ncsi.txt")
@router.get("/connecttest.txt")
@router.get("/success.txt")
def captive_detection(request: Request, db: DbSession = Depends(get_db)):
```

**What these are:** When a phone connects to WiFi, it pings a known URL (like `captive.apple.com` or `connectivitycheck.gstatic.com`). If the device gets a redirect (HTTP 302) instead of a success (HTTP 204), it knows it's behind a captive portal and opens the login page.

On a Raspberry Pi with iptables, all port 80/443 traffic is redirected to the local server. These endpoints provide the detection responses.

**Django analogy:** These are like health-check endpoints — simple responses with no template rendering.

### 8.4 `/portal` — the main page

```python
@router.get("/portal", response_class=HTMLResponse)
def portal_page(request: Request, db: DbSession = Depends(get_db)):
    mac = get_mac_from_ip(request.client.host)   # Resolve MAC from IP
    if mac:
        session = get_active_session_by_mac(db, mac)
        if session:
            return success.html                    # Already connected → show timer
    return portal.html                             # Not connected → show coin/voucher UI
```

**Flow:**
1. Get the client's MAC address from their IP (via ARP table, or synthetic in dev mode)
2. Check if that MAC has an active session
3. **Has session:** Show `success.html` with the remaining time countdown
4. **No session:** Show `portal.html` with coin and voucher tabs

**Context passed to templates:**
- `portal.html` gets `error=""`, `default_tab="coin"`, `COIN_POLL_INTERVAL=2`
- `success.html` gets `remaining_seconds`, `remaining_minutes`, `mac`

### 8.5 `/redeem` — voucher redemption

```python
@router.post("/redeem")
def redeem_voucher(request: Request, data: RedeemRequest, db: DbSession = Depends(get_db)):
    voucher = validate_voucher(db, data.code)
    if not voucher:
        return {"success": False, "message": "Invalid or expired voucher code"}
    # ... creates session, marks voucher used, grants firewall access
    return {"success": True, "message": "Access granted for 30 minutes", ...}
```

**The `data: RedeemRequest` parameter:** FastAPI auto-parses the request body into a `RedeemRequest` object (a Pydantic model with just a `code: str` field). This replaces Django's `request.POST.get("code")`.

**Django comparison:**
```python
# Django
@csrf_exempt
def redeem(request):
    data = json.loads(request.body)
    code = data.get("code")
    ...

# FastAPI
@router.post("/redeem")
def redeem(data: RedeemRequest, ...):
    code = data.code
    ...
```

**Why no `csrf_exempt`?** There's no CSRF middleware in this project. FastAPI doesn't have CSRF by default (Django does). If you expose this publicly, add CSRF protection or API tokens.

### 8.6 Coin endpoints

```python
@router.get("/coin-status")
def coin_status(request: Request, db: DbSession = Depends(get_db)):
    rate = get_val("coin_minutes_per_peso", "6")      # Read from DB settings
    timeout = get_val("coin_auto_grant_timeout", "10")
    minimum = get_val("coin_minimum_amount", "1")
    return coin_state.to_dict(rate, timeout, minimum)
    # Returns: {"amount":0, "minutes":0, "safe":false, "button_enabled":false,
    #            "auto_grant_seconds":10, "rate":6}
```

```python
@router.post("/coin-pulse")
def coin_pulse(data: CoinPulseRequest):
    coin_state.add_coin(data.amount)    # Add to the in-memory counter
    return {"success": True, "total_amount": coin_state.amount}
```

**The coin flow:** (See [Section 12](#12-coin-system--full-flow) for full detail)

1. Hardware (or simulator) sends `POST /coin-pulse {"amount": 1}` for each peso inserted
2. The portal polls `GET /coin-status` every 2 seconds to update the UI
3. When enough coins are in and the auto-grant timer expires, or the user clicks Connect:
   - `POST /coin-connect` is called
   - `process_coin()` reads the rate from DB, creates a voucher + session
   - The portal redirects to `/portal` which now shows `success.html`

### 8.7 Why sync (`def`) instead of async (`async def`)?

All route handlers use `def` not `async def`. This is intentional:

```python
# This
@router.get("/portal")
def portal_page(request, db = Depends(get_db)):
    ...

# NOT this
@router.get("/portal")
async def portal_page(request, db = Depends(get_db)):
    ...
```

**Reason:** SQLAlchemy calls are synchronous (blocking). If you use `async def`, the synchronous DB query blocks the entire event loop, preventing other requests from being processed. By using `def`, FastAPI runs the handler in a **thread pool**, so it doesn't block the event loop.

**Rule of thumb:** If your route calls any synchronous code (SQLAlchemy, file I/O, time.sleep), use `def`. If it's pure async (httpx, asyncio.sleep), use `async def`.

---

## 9. Admin Routes — `backend/admin_api.py`

All admin routes are prefixed with `/admin`. The prefix is set when creating the router:

```python
router = APIRouter(prefix="/admin")
```

**Django analogy:** This is like including `path("admin/", include(admin_urls))`.

### 9.1 Route table

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/admin` | `admin_dashboard` | Stats overview (total vouchers, revenue, active sessions) |
| GET | `/admin/vouchers` | `admin_vouchers` | Paginated voucher list |
| GET | `/admin/vouchers/create` | `admin_create_voucher_page` | Create voucher form |
| POST | `/admin/vouchers/create` | `admin_create_voucher` | API: generate new vouchers |
| POST | `/admin/vouchers/{id}/deactivate` | `admin_deactivate_voucher` | Deactivate a voucher |
| GET | `/admin/sessions` | `admin_sessions` | Active + recent sessions |
| POST | `/admin/sessions/{id}/disconnect` | `admin_disconnect_session` | Force-disconnect a session |
| GET | `/admin/settings` | `admin_settings_page` | Settings form |
| POST | `/admin/settings` | `admin_update_settings` | API: update coin rate settings |

### 9.2 Query parameter parsing

```python
@router.get("/vouchers")
def admin_vouchers(
    request: Request,
    page: int = Query(1, ge=1),     # ← Query parameter with validation
    db: DbSession = Depends(get_db),
):
```

**Django comparison:** This replaces `request.GET.get("page", 1)`. FastAPI automatically:
- Parses `?page=2` from the URL
- Validates it's an integer ≥ 1
- Returns a 422 error with a helpful message if validation fails

### 9.3 Template rendering

```python
return templates.TemplateResponse(
    request,
    "admin/vouchers.html",
    {
        "vouchers": vouchers,
        "stats": stats,
        "page": page,
    },
)
```

**Signature:** `TemplateResponse(request, template_name, context_dict)`

**Django analogy:** `render(request, "admin/vouchers.html", {...})`

**Difference from Django:**
- The `request` is always the first positional argument (Django puts it first too)
- Template path is relative to the `directory` set when creating `Jinja2Templates` (which is `backend/templates/`)

### 9.4 Error handling

```python
@router.post("/vouchers/{voucher_id}/deactivate")
def admin_deactivate_voucher(voucher_id: int, db: DbSession = Depends(get_db)):
    voucher = deactivate_voucher(db, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return {"success": True}
```

**Django analogy:** `raise HTTPException(...)` = `return HttpResponseNotFound()` or `raise Http404`. FastAPI returns a JSON error body automatically:
```json
{"detail": "Voucher not found"}
```

### 9.5 Content negotiation

Some admin endpoints return HTML (via `TemplateResponse`) and some return JSON (via dict). FastAPI doesn't care — it serializes dicts to JSON automatically.

**HTML endpoints:** `response_class=HTMLResponse`
**JSON endpoints:** No `response_class` — just return a dict

---

## 10. Voucher System — `backend/voucher.py`

This module manages the entire voucher lifecycle: generation, validation, usage tracking, and stats.

### 10.1 Code generation

```python
VOUCHER_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # No 0/O/1/I/L
VOUCHER_CODE_LENGTH = 8

def generate_code() -> str:
    return "".join(secrets.choice(VOUCHER_ALPHABET) for _ in range(VOUCHER_CODE_LENGTH))
```

Uses Python's `secrets` module (cryptographically random). The alphabet excludes ambiguous characters:
- `0` and `O` (zero vs letter O)
- `1`, `I`, `L` (one vs I vs L)

**Django analogy:** No equivalent built-in. You'd normally use `secrets.token_urlsafe()` or Django's `get_random_string()`.

### 10.2 `generate_vouchers()` — creating new vouchers

```python
def generate_vouchers(db, duration_minutes, price_pesos, count=1):
    vouchers = []
    for _ in range(count):
        code = _unique_code(db)          # Keep generating until unique
        voucher = Voucher(code=code, ...)
        db.add(voucher)
        vouchers.append(voucher)
    db.commit()                           # All vouchers saved in one transaction
```

Called from two places:
1. **Admin** creates vouchers manually (`admin_create_voucher`)
2. **Coin acceptor** creates a voucher when coins are inserted (`process_coin`)

### 10.3 `validate_voucher()` — checking a code

```python
def validate_voucher(db, code):
    return db.query(Voucher).filter(
        Voucher.code == code.upper().strip(),  # Case-insensitive
        Voucher.is_used == False,               # Not already used
        Voucher.is_active == True,              # Not deactivated
    ).first()
```

### 10.4 Stats

```python
def get_voucher_stats(db):
    return {
        "total": db.query(Voucher).count(),
        "used": db.query(Voucher).filter(Voucher.is_used == True).count(),
        "unused": total - used,
        "total_revenue": sum of all used voucher prices,
    }
```

---

## 11. Session Manager — `backend/session_manager.py`

Manages internet sessions — a session represents one device's access period.

### 11.1 `create_session()`

```python
def create_session(db, mac_address, ip_address, duration_minutes, voucher_code=None):
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
```

### 11.2 `get_active_session_by_mac()`

```python
def get_active_session_by_mac(db, mac_address):
    return db.query(Session).filter(
        Session.mac_address == mac_address,
        Session.is_active == True,
        Session.end_time > datetime.utcnow(),    # Not expired
    ).first()
```

Called on every `/portal` request to check if the user already has access.

### 11.3 `get_expired_sessions()`

Called by the background scheduler every 15 seconds. Finds sessions where `end_time` has passed but `is_active` is still `True`.

### 11.4 `get_remaining_seconds()`

```python
def get_remaining_seconds(session):
    remaining = (session.end_time - datetime.utcnow()).total_seconds()
    return max(0, int(remaining))
```

Used to show the countdown timer on `success.html`.

---

## 12. Coin System — Full Flow

This is the most complex part of the system. Here's the complete flow:

### 12.1 `CoinState` — in-memory state

**File:** `backend/coin_state.py`

A **thread-safe singleton** that holds the current coin insertion state. It's in-memory only — restarting the server resets it.

```python
class CoinState:
    _instance = None   # Singleton pattern

    def __init__(self):
        self.amount = 0             # Total pesos inserted
        self.safe = False           # Hardware safety sensor (always False in dev)
        self.last_pulse_time = 0.0  # Timestamp of most recent coin pulse
```

**Thread safety:** Uses `threading.Lock` on every method because FastAPI sync routes run in a thread pool. Without locks, two simultaneous coin pulses could corrupt the amount.

**`to_dict()`** serializes the state for the `/coin-status` endpoint. It calculates:
- `minutes = amount * minutes_per_peso` (e.g., 5 pesos × 6 min = 30 minutes)
- `auto_grant_seconds` = time remaining before auto-connect (counts down from `auto_grant_timeout`)
- `button_enabled` = true when `amount >= minimum_amount`

### 12.2 `CoinAcceptor.process_coin()` — coin → session

**File:** `backend/coin_acceptor.py`

Called when coins are ready to be converted to access:

```
process_coin(amount, mac_address, ip_address)
  │
  ├── 1. Read settings from DB (rate, timeout, minimum)
  ├── 2. Calculate: duration_minutes = amount * minutes_per_peso
  ├── 3. Check: no existing active session for this MAC
  ├── 4. Generate a voucher for this coin insertion
  ├── 5. Grant firewall access (iptables allow MAC)
  ├── 6. Create a session in the database
  ├── 7. Reset coin_state.amount to 0
  └── 8. Return success with session details
```

### 12.3 Complete coin flow (end-to-end)

```
1. User inserts ₱5 (5 pulses of ₱1 each)
         │
2. Each pulse → POST /coin-pulse {"amount": 1}
         │
3. coin_state.add_coin(1) runs for each pulse
         │   amount: 0 → 1 → 2 → 3 → 4 → 5
         │
4. Portal polls GET /coin-status every 2 seconds
         │   Returns: {amount: 5, minutes: 30, button_enabled: true, ...}
         │
5. Portal UI updates: shows ₱5, 30 min, Connect button enabled
         │
6. Auto-grant countdown starts at 10 seconds
         │   (Or user clicks Connect immediately)
         │
7. When countdown hits 0 (or connect clicked):
         │   POST /coin-connect is called
         │
8. process_coin(amount=5, mac=..., ip=...)
         ├── Reads rate=6 from DB
         ├── duration = 5 × 6 = 30 minutes
         ├── Generates voucher "K5L4DYZU" for ₱5 / 30 min
         ├── iptables: allow MAC address
         ├── Creates session in DB (30 min duration)
         └── Resets coin_state to 0
         │
9. Browser redirects to /portal
         │   Now detects active session → shows success.html
         │
10. success.html shows "29:59" countdown
         │   Polls /status every 10 seconds
         │
11. Background scheduler runs every 15 seconds
         │   When time expires: iptables: revoke MAC, mark session ended
         │
12. Phone detects WiFi is no longer functional
         │   Portal appears again on next WiFi attempt
```

### 12.4 Why both a voucher AND a session?

Every coin insertion creates a real voucher in the database. This means:
- Coin-based usage is trackable just like voucher sales
- The admin dashboard shows accurate revenue from coins
- If needed, the voucher could be reused or reissued

---

## 13. Scheduler — `backend/scheduler.py`

A background task that runs every `SESSION_CHECK_INTERVAL` seconds (default: 15) to expire sessions.

### 13.1 How it works

```python
async def session_expiry_loop():
    while not _stop_event.is_set():
        # Run the synchronous DB check in a thread
        await asyncio.to_thread(_expire_sessions)
        # Wait 15 seconds (or until stop signal)
        await asyncio.wait_for(_stop_event.wait(), timeout=SESSION_CHECK_INTERVAL)
```

**Key design choices:**
- Uses `asyncio.Event` for clean shutdown — when `stop()` is called, the `wait()` returns immediately instead of waiting the full 15 seconds
- DB calls run in a thread via `asyncio.to_thread()` to avoid blocking the event loop
- The scheduler is created as an asyncio task in `lifespan` and cancelled on shutdown

### 13.2 `_expire_sessions()`

```python
def _expire_sessions():
    expired = get_expired_sessions(db)     # Sessions past end_time but still active
    for session in expired:
        revoke_access(session.mac_address) # iptables: block this MAC
        end_session(db, session.id)        # DB: set is_active = False
```

---

## 14. Firewall — `backend/firewall.py`

Manages iptables rules on the Raspberry Pi. In dev mode, it logs what it would do without actually running commands.

### 14.1 Dev mode

```python
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
```

When `DEV_MODE=true` (default):
- `grant_access(mac)` → logs "would grant access to DE:VI:CE:127_0_0_1"
- `revoke_access(mac)` → logs "would revoke access for DE:VI:CE:127_0_0_1"
- `setup_captive_portal()` → logs "skipping iptables setup"
- `get_mac_from_ip(ip)` → returns `DE:VI:CE:{ip_with_underscores}` (synthetic MAC)

### 14.2 MAC resolution

```python
def get_mac_from_ip(ip_address: str) -> str | None:
    # Dev mode: return synthetic MAC
    # Production: read /proc/net/arp to find MAC for this IP
```

The `/proc/net/arp` file contains the kernel's ARP table — a mapping of IP addresses to MAC addresses for devices on the local network. This is how the Pi knows which MAC is trying to access the portal.

### 14.3 iptables chain

On a real Pi, the firewall creates an iptables chain called `PISO_WIFI`:

```
FORWARD chain
  → if from WiFi to WAN: jump to PISO_WIFI chain
  → if from WAN to WiFi (established): ACCEPT

PISO_WIFI chain:
  → Default: DROP
  → Allowed MACs: ACCEPT (inserted at position 1)
```

The captive portal redirect rule (NAT PREROUTING) sends all port 80/443 traffic to the local server.

**Django analogy:** There's no Django equivalent. This is system administration, not web development.

---

## 15. Templates (Jinja2 + Alpine.js)

### 15.1 Template structure

```
backend/templates/
├── portal.html              ← Main captive portal page
├── success.html             ← "Connected" page
└── admin/
    ├── base.html            ← Layout (sidebar + content)
    ├── dashboard.html       ← Stats cards
    ├── vouchers.html        ← Voucher table + pagination
    ├── create_voucher.html  ← Voucher creation form
    ├── sessions.html        ← Session tables
    └── settings.html        ← Coin settings form
```

### 15.2 Jinja2 vs Django Templates

Jinja2 is very similar to Django's template engine:

| Django Template | Jinja2 |
|---|---|
| `{{ var }}` | Same |
| `{% for x in list %}` | Same |
| `{% if condition %}` | Same |
| `{% extends "base.html" %}` | Same |
| `{% block name %}` | Same |
| `{% include "file.html" %}` | Same |
| `{{ var|default:"x" }}` | `{{ var|default("x") }}` |
| `{{ var|date:"Y-m-d" }}` | `{{ var|strftime("%Y-%m-%d") }}` (custom filter) |
| `{% url "name" %}` | No built-in URL reverse (use `{{ url_for }}` or hardcode) |
| `{{ request.path }}` | `{{ request.url.path }}` |

**Our custom filter:**
```python
# In utils.py
def ph_time(dt, fmt="%Y-%m-%d %H:%M"):
    # Converts UTC datetime to Asia/Manila timezone

# Usage in templates:
{{ voucher.created_at|ph_time }}
```

### 15.3 Alpine.js integration

Alpine.js powers the interactive parts of the UI without a build step (no webpack, no npm build).

**How a component is structured:**
```html
<div x-data="portal">
    <button @click="showTiers = !showTiers">Rate</button>     <!-- Event binding -->
    <div x-show="showTiers">...</div>                          <!-- Conditional display -->
    <span x-text="amount"></span>                              <!-- Text binding -->
    <input x-model="code">                                     <!-- Two-way binding -->
</div>
```

**Django analogy:** Alpine.js replaces the need for jQuery or vanilla JS for simple interactivity. Think of it as "smaller Vue.js without the build step."

### 15.4 How Jinja2 + Alpine work together

Server-side rendering (Jinja2) + client-side interactivity (Alpine) is a common pattern:

1. **Jinja2** injects server values:
   ```html
   <script>
       window.portalConfig = {
           error: "",
           pollInterval: 2000
       }
   </script>
   ```

2. **Alpine component** reads the config:
   ```javascript
   Alpine.data('portal', () => {
       const cfg = window.portalConfig || {}
       return {
           voucherError: cfg.error || '',
           init() {
               setInterval(() => this.poll(), cfg.pollInterval || 2000)
           }
       }
   })
   ```

3. **Alpine binds to the HTML:**
   ```html
   <div x-data="portal">
       <span x-text="voucherError"></span>
   </div>
   ```

This pattern keeps the JS file static (cacheable by browser) while letting Jinja2 inject dynamic values via a tiny inline `<script>` tag.

### 15.5 Admin layout — responsive sidebar

The admin uses an Alpine-powered collapsible sidebar:

```html
<body x-data="{ sidebarOpen: false }">
    <!-- Overlay (mobile only) -->
    <div x-show="sidebarOpen" @click="sidebarOpen = false"
         class="fixed inset-0 bg-black/50 z-40 sm:hidden"></div>

    <!-- Sidebar -->
    <aside :class="{ 'translate-x-0': sidebarOpen }"
           class="fixed ... -translate-x-full sm:translate-x-0 ...">
        <!-- Navigation links -->
    </aside>

    <!-- Content -->
    <main class="sm:ml-60 p-4 sm:p-8">
        <button @click="sidebarOpen = true" class="sm:hidden">☰</button>
        <h1>{% block heading %}Dashboard{% endblock %}</h1>
        {% block content %}{% endblock %}
    </main>
</body>
```

**On desktop:** Sidebar always visible (`sm:translate-x-0` pushes it on screen)
**On mobile:** Sidebar hidden by default (`-translate-x-full`), toggled by hamburger button

---

## 16. Static JS — `portal.js` and `success.js`

### 16.1 `portal.js` — the portal Alpine component

**Registered as:** `Alpine.data('portal', ...)`

**State variables:**
- `tab` — 'coin' or 'voucher'
- `amount`, `minutes`, `rate` — from `/coin-status`
- `buttonEnabled`, `autoGrantSeconds` — UI state
- `connecting` — true while connecting, shows loading overlay
- `voucherError`, `code`, `voucherLoading` — voucher form state
- `showTiers` — toggles the rate table visibility

**Computed properties (getters):**
- `label` — dynamic button text ("Insert Coin to Start", "₱5 (30 min)", etc.)
- `pct` — progress bar percentage
- `tiers` — rate table data (₱1, ₱5, ₱10, etc. with their minute equivalents)

**Methods:**
- `init()` — starts polling `/coin-status`
- `poll()` — fetches coin status, updates state, triggers auto-connect
- `connectCoin()` — sends POST /coin-connect
- `formatCode()` — formats voucher input (auto-dash, uppercase)
- `redeem()` — sends POST /redeem

**Polling logic:**
```javascript
init() {
    this.poll()                                           // Immediate first poll
    setInterval(() => this.poll(), cfg.pollInterval)       // Repeat every 2 seconds
}

async poll() {
    const d = await fetch('/coin-status').then(r => r.json())
    this.amount = d.amount
    this.rate = d.rate
    // Auto-connect if timer expired:
    if (d.auto_grant_seconds <= 0 && d.button_enabled && d.amount > 0)
        this.connectCoin()
}
```

### 16.2 `success.js` — the success page component

**Registered as:** `Alpine.data('success', ...)`

```javascript
{
    remaining: cfg.remaining,  // Seconds remaining (from Jinja2)
    init() {
        // Countdown tick every 1 second
        setInterval(() => { if (this.remaining > 0) this.remaining-- }, 1000)
        // Session check every 10 seconds
        setInterval(async () => {
            const d = await fetch('/status').then(r => r.json())
            if (!d.authenticated) window.location.href = '/portal'
        }, 10000)
    },
    get display() {
        return `${this.mins}:${String(this.secs).padStart(2, '0')}`
    }
}
```

### 16.3 Config injection pattern

Both components receive dynamic values the same way:

```html
<!-- In the HTML template (processed by Jinja2): -->
<script>
    window.portalConfig = {
        error: {{ error|tojson }},           ← "error" is a Jinja2 variable
        pollInterval: {{ COIN_POLL_INTERVAL * 1000 }}  ← COIN_POLL_INTERVAL is a Python constant
    }
</script>
<script defer src="/static/portal.js"></script>   ← Load AFTER config is set
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

**Script load order matters:**
1. Inline `<script>` sets `window.portalConfig` (runs immediately)
2. `<script defer src="/static/portal.js">` registers the `alpine:init` listener (runs after parse, before Alpine)
3. Alpine CDN loads and fires `alpine:init` (runs last) → the registered callback creates the component

---

## 17. Common Pitfalls for Django Devs

### 17.1 "Why is my route returning raw JSON instead of HTML?"

Make sure you have `response_class=HTMLResponse` on the decorator:
```python
# Returns HTML template
@router.get("/page", response_class=HTMLResponse)
def page():
    return templates.TemplateResponse(request, "page.html", {})

# Returns JSON
@router.get("/api")
def api():
    return {"key": "value"}
```

Without `response_class=HTMLResponse`, FastAPI assumes you're returning JSON (which is usually what you want, but not for templates).

### 17.2 "I forgot `Depends(get_db)` and now my route crashes"

Every route that uses the database must declare:
```python
def my_route(db: DbSession = Depends(get_db)):
```

The `Depends(get_db)` tells FastAPI to create a database session and pass it in. Without it, you'll get a runtime error about `db` not being defined.

### 17.3 "My `async def` route blocks the whole server"

If your route uses `async def` but calls synchronous code (like SQLAlchemy), it blocks the event loop. Use `def` instead:

```python
# BAD - blocks the event loop
@router.get("/portal")
async def portal_page(request, db = Depends(get_db)):
    vouchers = db.query(Voucher).all()       # ← synchronous, blocks!
    return {"count": len(vouchers)}

# GOOD - runs in thread pool
@router.get("/portal")
def portal_page(request, db = Depends(get_db)):
    vouchers = db.query(Voucher).all()
    return {"count": len(vouchers)}
```

**When to use `async def`:**
- Making HTTP requests with httpx
- Using asyncio.sleep()
- Reading/writing async file I/O

**When to use `def`:**
- Any SQLAlchemy call
- Any subprocess call
- Any time.sleep()
- Any CPU-bound operation

### 17.4 "My changes to Python files aren't showing"

FastAPI doesn't auto-reload. You need to stop the server (Ctrl+C) and restart. If you want auto-reload, run:
```bash
uvicorn backend.main:app --reload
```
(But note: the `_Server` class and custom signal handlers won't be used — this runs uvicorn directly.)

### 17.5 "Where did my database go? All data is gone"

The database is at `piso_wifi.db` in the project root. Deleting this file resets everything. There are no migrations — if you change a model, you need to delete the DB file and restart.

For production, you'll want to:
1. Use a proper database (PostgreSQL)
2. Set up Alembic for migrations
3. Store the DB file in a persistent location

### 17.6 "Why is there no CSRF?"

This project is designed as an internal appliance (like a router admin panel), not a public web app. CSRF protection is not implemented. If you expose the admin to the internet:
- Add CSRF tokens to forms
- Add authentication (admin login)
- Add rate limiting to `/coin-pulse` and `/redeem`

### 17.7 "How do I see available routes / API docs?"

FastAPI generates OpenAPI documentation automatically. Visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 17.8 "The portal shows raw code / JSON"

This usually means:
- The template file wasn't found (check the path in `Jinja2Templates(directory=...)`)
- The response is JSON instead of HTML (add `response_class=HTMLResponse`)
- The `x-data` inline object has a syntax error (check JavaScript console in browser)
- Alpine.js CDN failed to load (check network tab in dev tools)

### 17.9 "The admin sidebar overlaps on mobile"

The sidebar is hidden off-screen on mobile (`-translate-x-full`) and slides in when you click the hamburger (☰). Check:
- Alpine.js is loaded (look for `x-data` in the HTML source)
- The hamburger button is visible on small screens (`sm:hidden`)
- The overlay appears when sidebar is open

---

## 18. Running & Testing

### 18.1 Quick start

```bash
cd piso_wifi
python -m backend.main
# Open http://localhost:8000/portal
```

### 18.2 Simulate coins

```bash
# Insert ₱5 via pulses
python scripts/coin-simulator.py --amount 5

# Watch the portal update in your browser
# Click Connect or wait for auto-grant
```

### 18.3 Create a test voucher

```bash
# Via API:
curl -X POST http://localhost:8000/admin/vouchers/create \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 30, "price_pesos": 10, "count": 1}'

# Use the returned code at the portal
```

### 18.4 Testing all endpoints

```bash
# Check coin status
curl http://localhost:8000/coin-status

# Send a coin pulse
curl -X POST http://localhost:8000/coin-pulse \
  -H "Content-Type: application/json" \
  -d '{"amount": 1}'

# Connect (converts coins to session)
curl -X POST http://localhost:8000/coin-connect

# Check session status
curl http://localhost:8000/status

# View admin pages
open http://localhost:8000/admin
open http://localhost:8000/admin/settings
```

### 18.5 Check the API docs

```
http://localhost:8000/docs    ← Swagger UI
http://localhost:8000/redoc   ← ReDoc
```

---

## 19. Deploying on Raspberry Pi

### 19.1 Quick deploy

```bash
sudo bash scripts/setup_pi.sh
```

This installs hostapd, dnsmasq, configures iptables, and starts the server.

### 19.2 Manual steps

1. Install dependencies:
   ```bash
   sudo apt install hostapd dnsmasq iptables python3-pip
   pip install -r requirements.txt
   ```

2. Configure hostapd (WiFi access point) and dnsmasq (DHCP + DNS)

3. Set environment variables:
   ```bash
   export DEV_MODE=false
   export WIFI_IFACE=wlan0
   export WAN_IFACE=eth0
   ```

4. Start the server:
   ```bash
   python -m backend.main &
   ```

5. The firewall setup runs on first access via the portal routes

### 19.3 Dev mode vs production

| Feature | Dev Mode (default) | Production (`DEV_MODE=false`) |
|---|---|---|
| MAC addresses | Synthetic (`DE:VI:CE:127_0_0_1`) | Real from ARP table |
| iptables | Skipped (logged) | Executed with sudo |
| Internet access | Not affected | Controlled by firewall |
| Coin hardware | Simulated via API | Real GPIO/USB acceptor needed |
| Testing | Works on laptop | Requires Raspberry Pi |

---

## Need Help?

- **RTFM:** Start with this document
- **FastAPI docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy docs:** https://docs.sqlalchemy.org/
- **Alpine.js docs:** https://alpinejs.dev/
- **Tailwind CSS:** https://tailwindcss.com/docs
