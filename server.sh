#!/bin/bash

start() {
    nohup ./venv/bin/uvicorn main:app --port 8002 > server.log &
    echo $! > server.pid
    echo "Server started"
}

stop() {
    kill -15 $(cat server.pid)
    sleep 120
    if ps -p $(cat server.pid) > /dev/null; then
       kill -9 $(cat server.pid)
    fi
    rm server.pid
    echo "Server stopped"
}

restart() {
    stop
    start
}

case "$1" in 
start)   start ;;
stop)    stop ;;
restart) restart ;;
*) echo "Usage: $0 {start|stop|restart}" ;;
esac