# Quick Start Guide - LoRa Image Transfer System

## TL;DR - What You Need to Do

### 1️⃣ Raspberry Pi Setup (5 minutes)

```bash
# Install dependencies
sudo pip3 install opencv-python numpy --break-system-packages
sudo pip3 install adafruit-circuitpython-rfm9x --break-system-packages

# Copy the new scripts to your project folder
# (lora_transmit.py, workflow.py)

# Make executable
chmod +x workflow.py lora_transmit.py
```

### 2️⃣ Windows Setup (5 minutes)

```bash
# Install Python dependencies
pip install pyserial

# Test your USB dongle
python test_dongle.py
```

### 3️⃣ Run the System

**On Windows (start FIRST):**
```bash
python lora_receive.py
```

**On Raspberry Pi:**
```bash
# Plug in USB drive with images
python3 workflow.py --auto-mount
# Or specify path:
python3 workflow.py /media/usb0/images
```

**Done!** Images will be received in `received_images/` folder on Windows.

---

## What I Built for You

### New Scripts Created

1. **`lora_transmit.py`** - Raspberry Pi LoRa transmitter
   - Reads images from folder
   - Breaks them into packets
   - Sends via LoRa with checksums
   - Handles retries

2. **`lora_receive.py`** - Windows LoRa receiver
   - Auto-detects COM port
   - Receives packets
   - Reassembles files
   - Saves to disk

3. **`workflow.py`** - Complete automation
   - Runs red circle detection (your existing code)
   - Creates manifest (your existing code)
   - Transmits via LoRa (new)
   - All in one command!

4. **`test_dongle.py`** - USB dongle tester
   - Identifies your dongle type
   - Tests AT commands
   - Tests transparent mode
   - Provides recommendations

### Documentation Created

1. **`LORA_SETUP.md`** - Complete setup guide
2. **`WINDOWS_DONGLE_GUIDE.md`** - Dongle-specific help
3. **`QUICKSTART.md`** - This file!

---

## How It Works

```
[USB Drive] 
    ↓
[Raspberry Pi]
    ↓ Your existing code
[Red Circle Detection] → finds 10 images with red circles
    ↓ Your existing code  
[Create Manifest] → MD5 checksums
    ↓ NEW CODE
[LoRa Transmitter] → breaks into 250-byte packets
    ↓ ~915 MHz LoRa~
[LoRa Receiver] → Windows USB dongle
    ↓ NEW CODE
[File Reassembly] → saves complete images
    ↓
[received_images/] folder on Windows
```

**Your existing code:**
- ✅ Image detection (OpenCV) - `ImageSorting/sort.py`
- ✅ Manifest creation - `ChecksumBuilder/make_manifest.py`
- ✅ Checksum verification - `IntegrityVerifier/verify_manifest.py`
- ✅ Encryption/decryption - `Encryption+Decryption/`

**New code:**
- 🆕 LoRa packet protocol
- 🆕 File chunking and reassembly
- 🆕 Error detection (CRC16)
- 🆕 Workflow automation

---

## Important Notes

### ⏱ Speed Expectations

**LoRa is SLOW** (by design - it's for long range, low power):
- **Expected speed:** 5-10 kbps
- **100KB image:** 2-4 minutes
- **10 images (1MB total):** 20-40 minutes

At 10 feet, this is overkill, but it's educational! 📚

### 🔍 Your Windows USB Dongle

**IMPORTANT:** You need to identify your dongle type first!

```bash
# Run this on Windows:
python test_dongle.py
```

This will tell you:
- ✓ What COM port it's on
- ✓ What protocol it uses (AT commands vs transparent)
- ✓ If it's receiving data
- ✓ What modifications (if any) are needed

**Most dongles are:**
1. **Transparent** (85% chance) → works with current code ✓
2. **AT Command** (15% chance) → needs small modification

### 📡 Frequency Match

**Both devices MUST be 915 MHz:**
- ✓ Pi: Adafruit RFM95W @ 915MHz (confirmed)
- ❓ Windows: Your USB dongle (check specs!)

If frequencies don't match, **it won't work at all**.

---

## Troubleshooting Decision Tree

### Problem: "No COM port found"
→ Check Device Manager
→ Install driver (see LORA_SETUP.md)
→ Try different USB port

### Problem: "COM port found but no data"
→ Run `test_dongle.py`
→ Make sure Pi is transmitting
→ Check antenna connections
→ Verify 915MHz on both ends

### Problem: "Data received but corrupted"
→ Check packet checksums in output
→ Reduce transmission speed (increase delays)
→ Move closer / remove interference

### Problem: "Too slow!"
→ This is expected with LoRa (see speed notes above)
→ Consider alternatives: WiFi, Bluetooth, USB direct
→ Or just accept it as part of learning! 🎓

---

## File Checklist

Put these files in your project:

### Raspberry Pi
```
project/
├── workflow.py              ← NEW (automation script)
├── lora_transmit.py         ← NEW (transmitter)
├── ImageSorting/
│   ├── sort.py             ← YOUR EXISTING CODE
│   └── requirements.txt
├── ChecksumBuilder/
│   ├── make_manifest.py    ← YOUR EXISTING CODE
│   └── README.md
└── IntegrityVerifier/
    ├── verify_manifest.py  ← YOUR EXISTING CODE
    └── README.md
```

### Windows
```
windows/
├── lora_receive.py          ← NEW (receiver)
├── test_dongle.py           ← NEW (dongle tester)
├── LORA_SETUP.md            ← NEW (setup guide)
├── WINDOWS_DONGLE_GUIDE.md  ← NEW (dongle help)
└── QUICKSTART.md            ← NEW (this file)
```

---

## Step-by-Step First Run

### Part 1: Test Your Dongle (Windows)

```bash
# 1. Plug in your USB LoRa dongle
# 2. Check Device Manager - note the COM port
# 3. Run test:
python test_dongle.py

# Follow the prompts
# Note what it says about protocol type
```

**Expected output:**
```
Available COM Ports:
1. COM3
   Description: USB Serial Port
   *** Possible LoRa device (contains 'USB SERIAL') ***

Testing AT Commands:
...

Testing Transparent Mode (listening for 10 seconds):
⚠ Make sure Raspberry Pi is transmitting now!
```

### Part 2: Start Receiver (Windows)

```bash
# In one terminal:
python lora_receive.py -p COM3

# You should see:
LoRa Receiver initialized on COM3
Waiting for transmissions...
```

### Part 3: Prepare Pi (Raspberry Pi)

```bash
# Plug in USB drive with images
# Check it's mounted:
ls /media/pi/

# or auto-mount:
python3 workflow.py --auto-mount
```

### Part 4: Transmit! (Raspberry Pi)

```bash
# Run complete workflow:
python3 workflow.py /media/usb0/images

# You'll see:
# STEP 1: Detecting images with red circles
# ... (your existing sort.py output)
# STEP 2: Creating checksum manifest
# ... (your existing make_manifest.py output)
# STEP 3: Transmitting via LoRa
# ⚠ Make sure Windows receiver is running!
# Press Enter to start transmission...
```

**Press Enter** and watch the magic! ✨

### Part 5: Verify (Windows)

```bash
# After transmission completes:
cd IntegrityVerifier
python verify_manifest.py ../received_images

# Should show all checksums match!
```

---

## Next Steps If It Doesn't Work

### 1. Dongle Not Detected
- Read: `WINDOWS_DONGLE_GUIDE.md` → "Finding Your COM Port"
- Install driver if needed
- Run `test_dongle.py` again

### 2. Dongle Detected But No Data
- Verify Pi is transmitting (check console output)
- Run `test_dongle.py` while Pi transmits
- Check `LORA_SETUP.md` → "Troubleshooting"

### 3. Data Received But Corrupted
- Check checksums in receiver output
- Increase delays in `lora_transmit.py`
- Read about error handling in `LORA_SETUP.md`

### 4. Protocol Issues
- If `test_dongle.py` says "AT Command"
  → Read `WINDOWS_DONGLE_GUIDE.md` → "For AT Command Dongles"
- If says "Custom Protocol"
  → Provide dongle model for specific help
  → Or consider using second Pi as receiver

---

## Alternative: Faster Methods

If LoRa is too slow for your demo:

### Option 1: WiFi (FAST - seconds)
```bash
# Pi: Share folder
python3 -m http.server 8000

# Windows: Download
# Open http://<pi-ip>:8000 in browser
```

### Option 2: Bluetooth (MEDIUM - minutes)
```bash
# Setup bluetooth file transfer
# Much faster than LoRa at short range
```

### Option 3: USB Direct (INSTANT)
```bash
# Just move the USB drive!
# Most practical for 10 feet
```

**But LoRa is cooler for learning!** 🚀

---

## Support

### If You're Stuck

**Provide this info:**

1. **Dongle details:**
   - Brand/model (check label or purchase link)
   - What `test_dongle.py` reported

2. **Error messages:**
   - Complete error text
   - When it occurred (Pi or Windows?)

3. **What you tried:**
   - Which steps completed successfully
   - Where it failed

### Useful Commands for Debugging

```bash
# Windows - check COM ports:
python -m serial.tools.list_ports

# Windows - test serial:
python -m serial.tools.miniterm COM3 115200

# Pi - check SPI:
ls /dev/spi*

# Pi - check LoRa bonnet:
i2cdetect -y 1
```

---

## Success Checklist

- [ ] Dependencies installed (Pi and Windows)
- [ ] Windows USB dongle identified (`test_dongle.py`)
- [ ] COM port known
- [ ] Driver installed (if needed)
- [ ] Receiver running on Windows
- [ ] Pi workflow script ready
- [ ] USB drive with images plugged in
- [ ] Antennas connected on both ends
- [ ] Both devices are 915 MHz
- [ ] Coffee ready (for 20-40 minute wait) ☕

**Good luck!** 🎉

---

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│           QUICK COMMAND CARD                │
├─────────────────────────────────────────────┤
│                                             │
│ WINDOWS:                                    │
│   Test dongle:                              │
│     python test_dongle.py                   │
│                                             │
│   Start receiver:                           │
│     python lora_receive.py                  │
│                                             │
│   Verify files:                             │
│     cd IntegrityVerifier                    │
│     python verify_manifest.py               │
│            ../received_images               │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│ RASPBERRY PI:                               │
│   Complete workflow:                        │
│     python3 workflow.py --auto-mount        │
│                                             │
│   Manual transmission:                      │
│     python3 lora_transmit.py                │
│            with_red_circles                 │
│                                             │
│   Just detection:                           │
│     cd ImageSorting                         │
│     python3 sort.py /path/to/images         │
│                                             │
└─────────────────────────────────────────────┘
```

**Happy transmitting!** 📡✨
