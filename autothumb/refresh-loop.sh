#!/usr/bin/env bash

# OSError: inotify watch limit reached
# python3 main.py --watch
# exit 1

while true; do
	echo
	date
	time python3 main.py 
	sleep 3600
done

