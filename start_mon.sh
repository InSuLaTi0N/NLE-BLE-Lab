#!/bin/bash

echo "[*] 1. 停止干扰进程 (NetworkManager & wpa_supplicant)..."
sudo systemctl stop NetworkManager
sudo systemctl stop wpa_supplicant
sudo airmon-ng check kill 2>/dev/null

echo "[*] 2. 关闭默认的 wlan0 接口..."
sudo ifconfig wlan0 down

echo "[*] 3. 清理可能残留的 mon0..."
sudo iw dev mon0 del 2>/dev/null

echo "[*] 4. 创建纯净的 mon0 监听接口..."
sudo iw dev wlan0 interface add mon0 type monitor

echo "[*] 5. 激活 mon0 并调整发送队列 (缓解 Errno 105)..."
sudo ifconfig mon0 up
sudo ifconfig mon0 txqueuelen 3000

echo "[*] 6. 锁定初始信道 (例如信道 1)..."
sudo iw dev mon0 set channel 1

echo "[+] Nexmon mon0 初始化完成！"
iw dev mon0 info
