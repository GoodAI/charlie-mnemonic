#!/bin/bash

start() {
    nohup ./venv/bin/uvicorn main:app --port 8002 > server.log 2>&1 &
    echo $! > server.pid
    echo "Server started"
    if ! ps -p $! > /dev/null; then
        echo "Failed to start server."
        return 1
    fi
}

stop() {
    if [ ! -f server.pid ]; then
        echo "Server is not running."
        return
    fi
    
    local pid=$(cat server.pid)
    kill -15 "$pid"
    local count=0
    while ps -p "$pid" > /dev/null; do
        sleep 1
        count=$((count + 1))
        if [ "$count" -eq 30 ]; then
            echo "Server did not shut down gracefully; force-stopping."
            kill -9 "$pid"
            break
        fi
    done
    rm server.pid
    echo "Server stopped"
}

restart() {
    echo "Restarting server..."
    stop
    start
}

update() {
    echo "Updating server..."
    stop
    if [ -f "./venv/bin/activate" ]; then
        source ./venv/bin/activate
    else
        echo "Virtual environment not found. Please ensure the virtual environment is correctly set up."
        return 1
    fi
    if ! pip install -r requirements.txt; then
        echo "Failed to install requirements."
        return 1
    fi
    start
}

case "$1" in 
start)   start ;;
stop)    stop ;;
restart) restart ;;
update)  update ;;
*) echo "Usage: $0 {start|stop|restart|update}" ;;
esac