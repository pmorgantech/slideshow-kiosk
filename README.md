# Kiosk Slideshow

A self-contained kiosk system: a tablet acts as a remote control, and a
TV-connected laptop plays the selected slideshow fullscreen. Drop image folders
into `slideshows/`, point both devices at the same Python server, and you're
running. No app to build, no config files to write.

```
kiosk-slideshow/
├── server.py            # FastAPI app (control + display + image serving)
├── requirements.txt
├── start.sh             # convenience launcher
├── static/
│   ├── control.html     # tablet remote — tap a tile to switch slideshows
│   └── display.html     # fullscreen slideshow for the TV
└── slideshows/          # YOU fill this in
    ├── morning/         # one folder = one slideshow
    │   ├── 01.jpg
    │   └── 02.jpg
    ├── lunch/
    ├── specials/
    └── closing/
```

Each subfolder of `slideshows/` becomes one tile on the tablet. Folder name =
tile label. Images play in natural filename order (`2` before `10`), advancing
every 5 seconds — change `ADVANCE_SECONDS` in `server.py` to taste.

## 1. Install & run (on the laptop)

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` lets the tablet reach the server over Wi-Fi. For a USB-only
setup it's harmless to leave in.

## 2. Open the display (on the laptop)

Navigate to `http://localhost:8000/display` in a browser. The page requests
fullscreen automatically. If the browser blocks the auto-request, a single tap
or keypress will trigger it.

For a true kiosk launch (no browser chrome, fullscreen from the start):

```bash
chromium --kiosk --app=http://localhost:8000/display \
  --noerrdialogs --disable-infobars
```

(Use `chromium-browser`, `google-chrome`, or `firefox --kiosk` depending on
what's installed.) To launch on boot, drop that command into an autostart
`.desktop` file.

## 3. Connect the tablet

**USB (recommended — rock solid, no IP addresses):**

Enable Developer Mode + USB debugging on the tablet, install `adb` on the
laptop, plug in, then:

```bash
adb reverse tcp:8000 tcp:8000
```

The tablet's browser can now reach `http://localhost:8000/` through the cable.

**Wi-Fi:**

Point the tablet's browser at `http://<laptop-ip>:8000/`. If the laptop's IP
drifts, give it a DHCP reservation, or install `avahi-daemon` and use
`http://<hostname>.local:8000/`.

On the tablet, open the URL and choose **"Add to Home Screen"** so it launches
chromeless like a real app. A dedicated kiosk browser (e.g. Fully Kiosk) works
too if you want to lock the tablet down.

## How it works

- `GET /api/slideshows` — server scans `slideshows/` and returns each folder
  with its ordered image URLs.
- Tablet renders the tile grid; a tap `POST`s to `/api/select/{folder}`.
- The server broadcasts the selection over a WebSocket (`/ws`).
- The display page receives it and cuts instantly — it double-buffers and
  decodes each image before swapping, so there's no white flash.
- A freshly connected display or tablet is immediately sent the current
  selection, so everything self-syncs after a reboot or sleep.
- The display page requests fullscreen on load; if the browser blocks the
  auto-request, any tap or keypress triggers it.

## Adding or changing slideshows

Add or remove folders and images under `slideshows/`. The tablet picks up
changes on its next page refresh — no server restart needed.
