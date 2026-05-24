#!/bin/sh

. .venv/bin/activate

killall uvicorn

( sleep 5 && chromium --kiosk --app=http://localhost:8000/display --noerrdialogs --disable-infobars ) &

uvicorn server:app --host 0.0.0.0 --port 8000 &
