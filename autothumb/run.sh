#!/usr/bin/env bash
cd /opt/sipr0n/autothumb
(echo; echo; echo; echo starting; sudo -u www-data ./refresh-loop.sh) |tee -a /opt/sipr0n/autothumb/log.txt

