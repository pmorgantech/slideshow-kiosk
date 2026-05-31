#!/usr/bin/env python3
"""Slideshow switcher.

One web app, two views:
  /          -> control page (the picture grid you tap on the tablet)
  /display   -> the slideshow itself (run this fullscreen on the TV laptop)

A tap on the control page POSTs a selection; the server broadcasts it over a
WebSocket so the display cuts to that slideshow instantly.

Run:  uvicorn server:app --host 0.0.0.0 --port 8000
"""
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
SLIDESHOWS_DIR = BASE_DIR / "slideshows"   # one subfolder per slideshow
STATIC_DIR = BASE_DIR / "static"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
ADVANCE_SECONDS = 5   # how long each slide is shown before auto-advancing

SLIDESHOWS_DIR.mkdir(exist_ok=True)        # must exist before StaticFiles mount

app = FastAPI()


# ----------------------------------------------------------------------
# Slideshow discovery
# ----------------------------------------------------------------------
def natural_key(s: str):
    """Sort helper so 'slide2' comes before 'slide10'."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def list_slideshows():
    """Scan SLIDESHOWS_DIR. Each subfolder containing images is one slideshow."""
    shows = []
    for folder in sorted(SLIDESHOWS_DIR.iterdir(), key=lambda p: natural_key(p.name)):
        if not folder.is_dir():
            continue
        images = sorted(
            (f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTS),
            key=lambda p: natural_key(p.name),
        )
        if not images:
            continue
        shows.append({
            "id": folder.name,
            "name": folder.name,
            "images": [f"/img/{folder.name}/{img.name}" for img in images],
        })
    return shows


# ----------------------------------------------------------------------
# Shared state + WebSocket fan-out
# ----------------------------------------------------------------------
clients: set[WebSocket] = set()
current_selection: str | None = None


async def broadcast(message: dict):
    dead = set()
    for ws in clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)


def select_message(show: dict) -> dict:
    return {"type": "select", "show": show, "advance": ADVANCE_SECONDS}


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
app.mount("/img", StaticFiles(directory=SLIDESHOWS_DIR), name="img")


@app.get("/")
def control_page():
    return FileResponse(STATIC_DIR / "control.html")


@app.get("/display")
def display_page():
    return FileResponse(STATIC_DIR / "display.html")


@app.get("/api/slideshows")
def api_slideshows():
    return list_slideshows()


@app.post("/api/select/{show_id}")
async def api_select(show_id: str):
    global current_selection
    shows = {s["id"]: s for s in list_slideshows()}
    if show_id not in shows:
        raise HTTPException(404, f"No slideshow '{show_id}'")
    current_selection = show_id
    await broadcast(select_message(shows[show_id]))
    return {"ok": True, "selected": show_id}


@app.post("/api/stop")
async def api_stop():
    global current_selection
    current_selection = None
    await broadcast({"type": "idle"})
    return {"ok": True}


@app.post("/api/prev")
async def api_prev():
    await broadcast({"type": "prev"})
    return {"ok": True}


@app.post("/api/next")
async def api_next():
    await broadcast({"type": "next"})
    return {"ok": True}


@app.post("/api/pause")
async def api_pause():
    await broadcast({"type": "pause"})
    return {"ok": True}


@app.post("/api/resume")
async def api_resume():
    await broadcast({"type": "resume"})
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    # Bring a freshly connected client up to date with the current selection.
    shows = {s["id"]: s for s in list_slideshows()}
    if current_selection in shows:
        await ws.send_json(select_message(shows[current_selection]))
    else:
        await ws.send_json({"type": "idle"})
    try:
        while True:
            await ws.receive_text()   # no inbound messages expected; keeps socket open
    except WebSocketDisconnect:
        clients.discard(ws)
