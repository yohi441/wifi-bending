import asyncio
import logging
import os
import signal
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend.admin_api import router as admin_router
from backend.captive_portal import router as portal_router
from backend.config import HOST, PORT, SESSION_SECRET
from backend.database import init_db
from backend.firewall import setup_captive_portal
from backend.scheduler import session_expiry_loop, stop as stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task
    init_db()
    setup_captive_portal()
    _scheduler_task = asyncio.create_task(session_expiry_loop())
    yield
    stop_scheduler()
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass


def create_app() -> FastAPI:
    app = FastAPI(title="Piso WiFi", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)

    app.mount("/static", StaticFiles(directory="backend/static"), name="static")
    app.include_router(portal_router)
    app.include_router(admin_router)
    app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

    @app.get("/", response_class=HTMLResponse)
    def root():
        return RedirectResponse(url="/portal")

    @app.exception_handler(404)
    def not_found(request: Request, exc):
        return RedirectResponse(url="/portal")

    return app


app = create_app()


class _Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass


def main():
    config = uvicorn.Config(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = _Server(config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.add_signal_handler(signal.SIGINT, lambda: os._exit(0))
    loop.add_signal_handler(signal.SIGTERM, lambda: os._exit(0))

    try:
        loop.run_until_complete(server.serve())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
