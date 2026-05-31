#!/bin/sh
# Usage: ./slideshow.sh {start|stop|restart|status}

PIDFILE="$(dirname "$0")/.slideshow.pid"
PORT=8000

is_running() {
    [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

do_start() {
    if is_running; then
        echo "Already running (pid $(cat "$PIDFILE")). Use restart to reload."
        exit 1
    fi

    . "$(dirname "$0")/.venv/bin/activate"

    uvicorn server:app --host 0.0.0.0 --port "$PORT" &
    echo $! > "$PIDFILE"
    echo "Started uvicorn (pid $(cat "$PIDFILE")) on port $PORT."

    ( sleep 5 && chromium --kiosk --app=http://localhost:$PORT/display --noerrdialogs --disable-infobars ) &
}

do_stop() {
    if ! is_running; then
        echo "Not running."
        rm -f "$PIDFILE"
        return
    fi
    kill "$(cat "$PIDFILE")" && rm -f "$PIDFILE"
    echo "Stopped."
}

do_status() {
    if is_running; then
        echo "Running (pid $(cat "$PIDFILE"))."
    else
        echo "Not running."
    fi
}

case "${1}" in
    start)   do_start  ;;
    stop)    do_stop   ;;
    restart) do_stop; sleep 1; do_start ;;
    status)  do_status ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
