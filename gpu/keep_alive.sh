#!/bin/bash

# if not already detached, re-exec ourselves with setsid
if [ -z "$KEEPALIVE_DETACHED" ]; then
    export KEEPALIVE_DETACHED=1
    setsid "$0" "$@" </dev/null >/dev/null 2>&1 &
    exit 0
fi

# infinite loop to ping the GPU every minute
while true; do
  nvidia-smi > /dev/null
  sleep 60
done
