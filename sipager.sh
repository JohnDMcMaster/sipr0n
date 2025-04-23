#!/usr/bin/env bash
cd /opt/sipr0n
(echo; echo; echo; echo starting; sudo -u www-data python3 -u sipager.py "$@") |tee -a /var/www/lib/sipager.txt

