from scapy.all import *
from collections import namedtuple
import csv
import sys
import time
import struct
import os  # Required to execute system commands for channel switching
import threading
import select

# Interface Configuration
# Ensure 'mon0' is up and running before starting this script
s = conf.L2socket(iface="mon0")
prep = None
js = None
nextjs = None

stop_flag = False

# Generate random payload for the packet
bytelist = [random.randint(-128, 127) for _ in range(1526)]

# Define the structure for jamming settings from CSV
# Columns: Timestamp(s), Channel, Power, Period(ms), Length(bytes)
JamSetting = namedtuple("JamSetting", "timestamp channel power period length")

def get_ip_address():
    return "127.0.0.1"

def listen_for_enter():
    global stop_flag
    print "[*] Press ENTER to stop the program..."
    try:
        raw_input()
        stop_flag = True
        print "\n[!] ENTER pressed. Stopping..."
    except:
        pass

def update(js):
    """
    Updates the packet configuration and switches the hardware channel.
    """
    global prep
    
    # 1. HARDWARE SWITCHING
    # This command forces the physical network card to change frequency.
    # Note: Switching channels takes time (approx 20-50ms). 
    # If the CSV interval is too fast, the driver may crash (-110 error).
    current_channel = int(js.channel)
    print "[-] Switching hardware to Channel %d" % current_channel
    os.system("iw dev mon0 set channel %d" % current_channel)

    # 2. PACKET CONSTRUCTION
    # Create the Radiotap header
    rt = RadioTap(len=18, present='Flags+Rate+Channel+dBm_AntSignal+Antenna')
    rt.Rate = 2
    rt.Channel = current_channel
    rt.dBm_AntSignal = -1 * int(js.power)
    
    # Create the 802.11 Header (Broadcast)
    hdr = Dot11(addr1='ff:ff:ff:ff:ff:ff', addr2='00:11:22:33:44:55', addr3='00:11:22:33:44:55')

    # Limit payload length to prevent "Message too long" errors
    l = int(js.length)
    if l > 1400: 
        l = 1400
    
    sub = bytelist[0:l]
    buf = struct.pack('%sb' % l, *sub)
    pl = Raw(load=buf)

    # Assemble the packet
    doty = hdr/pl
    pkt = rt/doty
    prep = pkt.build()
    
    print "[-] Configuration updated: Time=%s, Ch=%d, Pwr=%s" % (js.timestamp, current_channel, js.power)

# Main Execution Loop
start = None

enter_thread = threading.Thread(target=listen_for_enter)
enter_thread.daemon = True
enter_thread.start()

# Open the CSV file provided as an argument
with open(sys.argv[1], mode="r") as csvfile:
    reader = csv.reader(csvfile, quoting=csv.QUOTE_NONNUMERIC)
    start = time.time()
    
    while not stop_flag:
        # Initialize the first setting
        if nextjs is None:
            try:
                js = JamSetting(*next(reader))
                update(js)
            except StopIteration:
                print "[!] End of CSV file reached."
                break
        else:
            js = nextjs

        # Try to read the next line in the CSV to know when to switch
        try:
            nextjs = JamSetting(*next(reader))
        except StopIteration:
            # If no more lines, continue using the last setting indefinitely
            # or you can choose to break here.
            nextjs = None

        # Inner loop: Send packets until it is time to switch to the next setting
        while not stop_flag:
            # Check if it is time to switch to the next configuration
            # Note: Removed '/1e9'. Assumes CSV timestamp is in SECONDS.
            if (nextjs is not None) and (time.time() > (start + nextjs.timestamp)):
                update(nextjs)
                break # Break inner loop to update 'js' to 'nextjs'
            
            # Send the packet if power is not 0
            if js.power != 0:
                s.send(prep)
            
            # Sleep between packets (Period is in milliseconds in CSV)
            if js.period > 0:
                time.sleep(js.period / 1000.0)

print "[*] Program terminated."
