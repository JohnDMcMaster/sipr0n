#!/usr/bin/env bash
ln -s /opt/sipr0n/autothumb/autothumb.service /etc/systemd/system/
ln -s /opt/sipr0n/sipager.service /etc/systemd/system/
ln -s /opt/sipr0n/simapper.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable autothumb.service
sudo systemctl enable sipager.service
sudo systemctl enable simapper.service

sudo systemctl start autothumb.service
sudo systemctl start sipager.service
sudo systemctl start simapper.service

echo "Checking"
sleep 1
sudo systemctl status autothumb.service
sudo systemctl status sipager.service
sudo systemctl status simapper.service
