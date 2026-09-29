#!/bin/bash

echo "[*] 1. Stopping interfering processes (NetworkManager & wpa_supplicant)..."
sudo systemctl stop NetworkManager
sudo systemctl stop wpa_supplicant
sudo airmon-ng check kill 2>/dev/null

echo "[*] 2. Disabling the default wlan0 interface..."
sudo ifconfig wlan0 down

echo "[*] 3. Removing any existing mon0 interface..."
sudo iw dev mon0 del 2>/dev/null

echo "[*] 4. Creating a clean mon0 monitor interface..."
sudo iw dev wlan0 interface add mon0 type monitor

echo "[*] 5. Activating mon0 and increasing the TX queue length (to reduce Errno 105)..."
sudo ifconfig mon0 up
sudo ifconfig mon0 txqueuelen 3000

echo "[*] 6. Setting the initial Wi-Fi channel (e.g., channel 1)..."
sudo iw dev mon0 set channel 1

echo "[+] Nexmon mon0 initialization completed!"
iw dev mon0 info