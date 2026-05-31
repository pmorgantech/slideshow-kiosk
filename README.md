# Kiosk Slideshow

A self-contained kiosk system: a **control host** (ideally a tablet) provides a
touch interface for selecting and navigating slideshows, while the **display
host** runs the server and plays the selected slideshow fullscreen on an attached
screen. Drop image folders into `slideshows/`, point both devices at the same
server, and you're running. No app to build, no config files to write.

```
kiosk-slideshow/
├── server.py            # FastAPI app (control + display + image serving)
├── requirements.txt
├── slideshow.sh         # service script (start/stop/restart/status)
├── static/
│   ├── control.html     # control host UI — tap a tile to switch slideshows
│   └── display.html     # fullscreen slideshow for the display host
└── slideshows/          # YOU fill this in
    ├── morning/         # one folder = one slideshow
    │   ├── 01.jpg
    │   └── 02.jpg
    ├── lunch/
    ├── specials/
    └── closing/
```

Each subfolder of `slideshows/` becomes one tile on the control host. Folder
name = tile label. The first image in the folder is used as the tile thumbnail.
Images play in natural filename order (`2` before `10`), advancing every 5
seconds — change `ADVANCE_SECONDS` in `server.py` to taste.

## 1. Install & run the server on the display host

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Or use the service script:

```bash
./slideshow.sh start     # start server + open display in kiosk browser
./slideshow.sh stop      # stop the server
./slideshow.sh restart   # stop then start
./slideshow.sh status    # check whether the server is running
```

`--host 0.0.0.0` makes the server reachable from the control host over the
network. For a USB-only setup it's harmless to leave in.

## 2. Open the display

On the display host, navigate to `http://localhost:8000/display` in a browser.
The page requests fullscreen automatically; if the browser blocks the
auto-request, a single tap or keypress will trigger it.

For a true kiosk launch (no browser chrome, fullscreen from the start):

```bash
chromium --kiosk --app=http://localhost:8000/display \
  --noerrdialogs --disable-infobars
```

(Use `chromium-browser`, `google-chrome`, or `firefox --kiosk` depending on
what's installed.) To launch on boot, drop that command into an autostart
`.desktop` file. The `start.sh` script does this automatically.

## 3. Connect the control host

**USB (recommended — no IP addresses, rock solid):**

Enable Developer Mode + USB debugging on the control host, install `adb` on the
display host, plug in, then:

```bash
adb reverse tcp:8000 tcp:8000
```

The control host's browser can now reach `http://localhost:8000/` through the
cable.

**Wi-Fi:**

Point the control host's browser at `http://<display-host-ip>:8000/`. If the
IP drifts, give the display host a DHCP reservation, or install `avahi-daemon`
and use `http://<hostname>.local:8000/`.

On the control host, open the URL and choose **"Add to Home Screen"** so it
launches chromeless like a real app. A dedicated kiosk browser (e.g. Fully
Kiosk) works too if you want to lock the device down.

## How it works

- `GET /api/slideshows` — server scans `slideshows/` and returns each folder
  with its ordered image URLs.
- The control host renders a tile grid; tapping a tile `POST`s to
  `/api/select/{folder}`.
- The server broadcasts the selection over a WebSocket (`/ws`).
- The display receives it and cuts to the new slideshow instantly — images are
  double-buffered and decoded before swapping to avoid any white flash.
- Playback controls (`<` prev, `||` pause, `>` next) appear on the control host
  once a slideshow is selected. A **Back** button returns to the tile grid
  without interrupting the display.
- A freshly connected client is immediately sent the current state, so
  everything self-syncs after a reboot, sleep, or server restart.

## Adding or changing slideshows

Add or remove folders and images under `slideshows/`. The control host picks up
changes on its next page refresh — no server restart needed.
