# NLE-BLE-Lab

This repository is a byproduct of the **NLE & BLE experiment**, aimed at generating continuous and controllable channel interference to evaluate BLE and SLE communication quality.

The interference generation is primarily based on **Nexmon** and **JamLab**. For more detailed information, please visit:
- [Nexmon](https://github.com/seemoo-lab/nexmon)
- [JamLab](https://github.com/TuGraz-ITI/JamLab-NG)

This repository focuses on:
- WiFi firmware updates for Raspberry Pi 3B+
- Detailed steps for interference generation

The goal is to help beginners use Nexmon for jamming more easily while avoiding common bad gates.

---

## Introduction

Based on multiple attempts and verifications by the author and other contributors, we have **simplified unnecessary steps from the original repository** and ensured a stable, reproducible workflow.

---

## Installation Steps

### 1. Install Raspberry Pi OS

#### Why Not Use rpi-update for Kernel Downgrade?

The original tutorial uses `rpi-update` to downgrade the kernel on the latest Raspberry Pi 3B+ system. However, after multiple tests, we found:

- **The downgrade process makes the system fragile**: After downgrading the kernel to version 5.4.72, the header files and other dependencies remain at the latest version. This often causes errors during subsequent `apt update` and kernel installation.
- **Never use `apt upgrade`**: It will confuse the system. If your kernel has just been rebooted to 5.4, running `upgrade` will restore it to the latest version, **which will crash the Raspberry Pi system**.

#### Recommended Solution: Download a Stable 5.4 Version System

We recommend downloading a stable system image from the official Raspberry Pi source:

**Download Link:**
https://downloads.raspberrypi.org/raspios_armhf/images/raspios_armhf-2020-08-24/2020-08-20-raspios-buster-armhf.zip


#### Flashing Steps

1. Download the `.zip` file above to your computer
2. Open **Raspberry Pi Imager**
3. Select device: **Raspberry Pi 3B**
4. Select OS: Click **"Use custom"**, then select the `.zip` file you just downloaded
5. Select storage: Choose your SD card
6. Click **"Write"** to start flashing

---

### 2. Update Software Sources & Install Dependencies

After installing the stable Raspberry Pi OS, verify the kernel version:

```bash
uname -r
```

The output should be `5.4.51-v7+`, which indicates a 32-bit system with kernel version 5.4.
However, the Raspberry Pi OS 5.4 version is based on Debian Buster (legacy version), which is no longer officially supported, and the original software sources have become invalid. Therefore, to ensure stable software updates, you need to use the archive sources.

Edit the main source file:

```bash
sudo nano /etc/apt/sources.list
```

Replace the contents with:

```bash
deb http://legacy.raspbian.org/raspbian/ buster main contrib non-free rpi
```

Edit the secondary source file:

```bash
sudo nano /etc/apt/sources.list.d/raspi.list
```

Replace the contents with:

```bash
deb http://legacy.raspberrypi.org/debian/ buster main
```

After editing, update the software sources:

```bash
sudo apt-get update
```

**Warning**: Do NOT use `apt upgrade` ever!

#### Install Kernel Headers

After updating, we can install the dependencies. First, install the kernel headers that match your kernel version. We recommend downloading the corresponding header package and installing it manually:

```bash
wget http://archive.raspberrypi.org/debian/pool/main/r/raspberrypi-firmware/raspberrypi-kernel-headers_1.20200819-1_armhf.deb
sudo dpkg -i raspberrypi-kernel-headers_1.20200819-1_armhf.deb
```

Then install the remaining dependencies:

```bash
sudo apt install git libgmp3-dev gawk qpdf bison flex make autoconf libtool texinfo tcpdump
```

### 3. Configure Nexmon

#### Clone the Repository

```bash
git clone https://github.com/seemoo-lab/nexmon.git
cd nexmon
```

#### Verify the required libraries

```bash
ls -l /usr/lib/arm-linux-gnueabihf/
```

If `libisl.so.10` does not exist, compile it from source:

```bash
cd buildtools/isl-0.10
./configure
make
make install
ln -s /usr/local/lib/libisl.so /usr/lib/arm-linux-gnueabihf/libisl.so.10
```

If `libmpfr.so.4` does not exist, compile it from source:

```bash
cd buildtools/mpfr-3.1.4
autoreconf -f -i
./configure
make
make install
ln -s /usr/local/lib/libmpfr.so /usr/lib/arm-linux-gnueabihf/libmpfr.so.4
```

#### Navigate back to the Nexmon root directory and set up the environment:

```bash
cd ../..
source setup_env.sh
make
```

#### Select the Firmware Patch

Since we are using the Raspberry Pi 3B+, the corresponding WiFi firmware is bcm43455c0. We select the 7_45_206 patch for this firmware. For information about different patches, please refer to the [Nexmon documentation](https://github.com/seemoo-lab/nexmon).

```bash
cd patches/bcm43455c0/7_45_206/nexmon/
```

#### Compile the Firmware Patch

```bash
make
```

If you encounter errors such as:
- Redefinition of `brcmf_debugfs_get_devdir`
- Redefinition of `brcmf_debugfs_add_entry`
- Redefinition of `brcmf_debug_create_memdump`

This indicates that functions in `debug.c` conflict with the header files. To resolve this, you need to comment out the duplicate function definitions:

```bash
cd ../../../driver/brcmfmac_5.4.y-nexmon
nano debug.c
```

Comment out the following three functions in `debug.c`:
- `brcmf_debug_create_memdump`
- `brcmf_debugfs_get_devdir`
- `brcmf_debugfs_add_entry`

Save the file with `Ctrl + O` and exit with `Ctrl + X`.

Then return to the Nexmon patch directory and rebuild:

```bash
cd ../../bcm43455c0/7_45_206/nexmon/
make clean
make
```

Create a backup of the original firmware:

```bash
make backup-firmware
```

Install the patched firmware:

```bash
make install-firmware
```

#### Install nexutil

From the root directory of nexmon switch to the nexutil folder: cd ~/nexmon/utilities/nexutil/. Compile and install nexutil: 

```bash
make && make install
```

*Optional*: To make the RPI3 load the modified driver after reboot, find the path of the default driver at reboot:

```bash
modinfo brcmfmac
```

the first line should be the full path, please copy that.

Backup the original driver:
```bash
mv "<PATH TO THE DRIVER>/brcmfmac.ko" "<PATH TO THE DRIVER>/brcmfmac.ko.orig"
```

Copy the modified driver:
```bash
cp /home/pi/nexmon/patches/driver/brcmfmac_5.4.y-nexmon/brcmfmac.ko "<PATH TO THE DRIVER>/"
```

Probe all modules and generate new dependency: 
```bash
depmod -a
reboot
```
The new driver should be loaded by default after reboot. 

### 4. Install JamLab

#### Clone the Repository

```bash
git clone https://github.com/TuGraz-ITI/JamLab-NG.git
```

#### Install Scapy

```bash
pip install scapy==2.4.5
```

