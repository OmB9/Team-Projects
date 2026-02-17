# LoRa Image Transmission System

Complete system for detecting images with red circles and transmitting them via LoRa from Raspberry Pi to Windows.

## Hardware Requirements

### Raspberry Pi Side
- Raspberry Pi (any model with 40-pin GPIO)
- **Adafruit LoRa Radio Bonnet with OLED - RFM95W @ 915MHz** (Product ID: 4074)
- USB drive with images
- Power supply

### Windows Side
- Windows laptop/PC
- **915MHz LoRa USB dongle** (your USB device with antenna)
- USB port

---

## Quick Start

### 1. Raspberry Pi Setup

```bash
# Install dependencies
sudo pip3 install opencv-python numpy --break-system-packages
sudo pip3 install adafruit-circuitpython-rfm9x --break-system-packages

# Make scripts executable
chmod +x workflow.py lora_transmit.py

# Run complete workflow
python3 workflow.py /media/usb0/images
# or auto-detect USB:
python3 workflow.py --auto-mount
```

### 2. Windows Setup

```bash
# Install Python dependencies
pip install pyserial

# Find your COM port (check Device Manager)
# Look for "USB Serial" or similar under "Ports (COM & LPT)"

# Run receiver
python lora_receive.py -p COM3
# or auto-detect:
python lora_receive.py
```

---

## Workflow Overview

The complete process:

```
USB Drive → Red Circle Detection → Create Manifest → LoRa Transmission → Windows Receiver
```

### Automatic Workflow (Recommended)

```bash
# On Raspberry Pi:
python3 workflow.py /path/to/usb/images

# On Windows (start BEFORE Pi transmission):
python lora_receive.py
```

### Manual Steps

If you want to run steps individually:

```bash
# Step 1: Detect red circles
cd ImageSorting
python3 sort.py /path/to/images -o with_red_circles

# Step 2: Create manifest
cd ChecksumBuilder
python3 make_manifest.py with_red_circles

# Step 3: Transmit
python3 lora_transmit.py with_red_circles
```

---

## Important Technical Details

### LoRa Configuration

The system is configured for **maximum speed at short range** (10 feet):

```python
Frequency: 915.0 MHz
Spreading Factor: 7 (fastest)
Bandwidth: 250 kHz (widest)
Coding Rate: 5 (lowest overhead)
TX Power: 23 dBm (maximum)

Expected Speed: ~5-10 kbps
```

### File Transfer Protocol

Files are broken into packets:
- **Max packet size**: 250 bytes (RFM95W hardware limit)
- **Header**: 10 bytes (metadata + checksum)
- **Data per packet**: 240 bytes
- **CRC16 checksum**: Each packet verified

**Transmission time estimates:**
- 100 KB image: ~2-4 minutes
- 500 KB image: ~10-20 minutes
- 10 images (100KB each): ~20-40 minutes total

### Packet Structure

```
Header (10 bytes):
┌─────────────┬─────────┬────────────┬──────────────┬──────────┬──────────┐
│ Packet Type │ File ID │ Packet Num │ Total Packets│ Data Len │ Checksum │
│   (1 byte)  │(1 byte) │  (2 bytes) │   (2 bytes)  │(2 bytes) │(2 bytes) │
└─────────────┴─────────┴────────────┴──────────────┴──────────┴──────────┘

Data (up to 240 bytes):
┌──────────────────────────────────────────┐
│          File data chunk                 │
└──────────────────────────────────────────┘
```

---

## Windows USB LoRa Dongle Setup

### Finding Your COM Port

**Method 1: Device Manager**
1. Open Device Manager (Win+X → Device Manager)
2. Expand "Ports (COM & LPT)"
3. Look for your LoRa device (might be labeled as "USB Serial", "CP2102", "CH340", etc.)
4. Note the COM port number (e.g., COM3)

**Method 2: Python Auto-detect**
```python
python lora_receive.py  # Will auto-scan and list available ports
```

### Common LoRa USB Dongles

Your 915MHz USB dongle is likely one of these:

1. **RFM95W-based USB adapter**
   - Uses CP2102 or FT232 USB-to-serial chip
   - Shows up as "USB Serial Device"
   - Baudrate: 115200 (most common) or 57600

2. **LoRa USB Stick (generic)**
   - Uses CH340 USB-to-serial chip
   - May require CH340 driver installation
   - Baudrate: 115200

### Driver Installation (if needed)

If Windows doesn't recognize your device:

**For CP2102:**
- Download from: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

**For CH340:**
- Download from: http://www.wch-ic.com/downloads/CH341SER_EXE.html

**For FTDI (FT232):**
- Download from: https://ftdichip.com/drivers/vcp-drivers/

---

## Troubleshooting

### Raspberry Pi Issues

**Problem: "No LoRa device found"**
```bash
# Check if bonnet is properly seated on GPIO pins
# Verify I2C and SPI are enabled:
sudo raspi-config
# → Interface Options → Enable SPI and I2C

# Test SPI:
ls /dev/spi*
# Should show: /dev/spidev0.0 /dev/spidev0.1
```

**Problem: "ImportError: No module named 'board'"**
```bash
# Reinstall CircuitPython libraries:
sudo pip3 install --upgrade adafruit-blinka adafruit-circuitpython-rfm9x --break-system-packages
```

**Problem: Images not detected**
```bash
# Test red circle detection manually:
cd ImageSorting
python3 sort.py /path/to/test/images

# Adjust sensitivity (in sort.py):
# Lower circularity_threshold (default 0.4) to detect rougher circles
# Lower min_area (default 500) to detect smaller circles
```

### Windows Issues

**Problem: "COM port not found"**
1. Check Device Manager for the device
2. Install appropriate driver (see Driver Installation above)
3. Manually specify port: `python lora_receive.py -p COM3`

**Problem: "Access denied to COM port"**
- Close any other programs using the port (Arduino IDE, PuTTY, etc.)
- Try a different USB port
- Restart Windows

**Problem: "No data received"**
```bash
# Test serial connection:
python -m serial.tools.miniterm COM3 115200

# Verify LoRa dongle is working:
# - LED should blink when receiving (if present)
# - Check antenna is properly connected
```

### General Issues

**Problem: Transmission too slow**
- This is normal! LoRa is designed for long range, not high speed
- At 5-10 kbps, expect ~20-40 minutes for 10 images
- Consider alternatives for faster transfer (see below)

**Problem: Packet checksum failures**
- Move devices closer together (eliminate interference)
- Ensure antennas are properly connected
- Check for metal objects or WiFi routers nearby (interference)
- Try reducing TX power: `self.rfm9x.tx_power = 13`

**Problem: Files incomplete on Windows**
- Check packet statistics in receiver output
- Increase retry count in transmitter (currently 3)
- Add delays between packets (increase `time.sleep()` values)

---

## Alternative Solutions

### If LoRa is too slow

At 10 feet distance, LoRa is overkill. Consider:

**1. WiFi/Network Transfer** (Fastest - seconds)
```bash
# Pi: Start HTTP server
python3 -m http.server 8000

# Windows: Download files
# Navigate to http://<pi-ip>:8000 in browser
```

**2. Bluetooth Transfer** (Fast - minutes)
- Use `bluetooth-sendfile` on Pi
- Much faster than LoRa at short range

**3. USB Transfer** (Instant)
- Simply move the USB drive from Pi to Windows
- Most practical for this distance!

### Why Use LoRa?

LoRa makes sense when:
- Long distance required (>100m)
- No line of sight
- Low power consumption needed
- Wireless licensing restrictions
- Educational/learning purposes ✓ (your case!)

---

## File Structure

```
project/
├── workflow.py              # Complete automation script
├── lora_transmit.py         # Pi LoRa transmitter
├── lora_receive.py          # Windows LoRa receiver
├── ImageSorting/
│   ├── sort.py             # Red circle detection
│   └── requirements.txt
├── ChecksumBuilder/
│   ├── make_manifest.py    # Create MD5 checksums
│   └── README.md
├── IntegrityVerifier/
│   ├── verify_manifest.py  # Verify checksums
│   └── README.md
└── Encryption+Decryption/
    ├── Encryption.py
    └── Decryption.py
```

---

## Testing the System

### Test 1: Red Circle Detection
```bash
cd ImageSorting
python3 sort.py SampleImages
# Should create with_red_circles/ folder with detected images
```

### Test 2: Manifest Creation
```bash
cd ChecksumBuilder
python3 make_manifest.py ../ImageSorting/with_red_circles
# Should create manifest.md5
```

### Test 3: LoRa Transmitter (Pi)
```bash
# Test with small file first
echo "test" > test.txt
python3 lora_transmit.py .
```

### Test 4: LoRa Receiver (Windows)
```bash
# Should be running before Pi transmits
python lora_receive.py -p COM3
# Watch for incoming packets
```

### Test 5: Verify Integrity (Windows)
```bash
cd IntegrityVerifier
python verify_manifest.py ../received_images
# Should show all checksums match
```

---

## Advanced Configuration

### Adjusting LoRa Settings

In `lora_transmit.py`, you can modify:

```python
# For longer range (slower speed):
self.rfm9x.spreading_factor = 12  # Default: 7
self.rfm9x.signal_bandwidth = 125000  # Default: 250000

# For more reliability:
self.rfm9x.coding_rate = 8  # Default: 5 (more error correction)

# Packet delays (if getting errors):
time.sleep(0.5)  # Increase from 0.2s
```

### Custom Packet Size

If you're getting many failures, try smaller packets:

```python
MAX_PAYLOAD = 128  # Reduce from 250
```

---

## Performance Metrics

Based on RFM95W specifications:

| Setting | Speed | Range | Reliability |
|---------|-------|-------|-------------|
| SF7, BW250, CR5 | ~10 kbps | <2 km | Good at short range |
| SF12, BW125, CR8 | ~0.3 kbps | ~15 km | Excellent |
| Your config | ~5-10 kbps | <2 km | Excellent at 10 feet |

**Estimated transmission times:**
- 10 images @ 100KB each = 1 MB
- At 8 kbps effective rate = ~125 seconds = **~2 minutes**
- Add overhead (headers, retries, delays) = **~20-40 minutes total**

---

## Safety Notes

⚠ **Regulatory Compliance:**
- 915 MHz is ISM band in USA (license-free)
- Max power 30 dBm EIRP (this setup uses 23 dBm)
- Must not cause interference to licensed services

⚠ **Hardware:**
- Don't operate LoRa modules without antenna (can damage radio)
- Ensure proper antenna connection before powering on
- Check antenna is rated for 915 MHz

---

## Support & Resources

### Documentation
- Adafruit RFM95W Guide: https://learn.adafruit.com/adafruit-rfm69hcw-and-rfm96-bonnet-radio-bonnets-for-raspberry-pi
- CircuitPython RFM9x: https://docs.circuitpython.org/projects/rfm9x/en/latest/

### Debugging
- Enable verbose output: Add `-v` flag to scripts
- Check LoRa register settings: Use `i2cdetect -y 1` on Pi
- Monitor serial traffic: Use PuTTY or Arduino Serial Monitor on Windows

---

## License & Credits

Scripts based on your existing codebase:
- Image sorting (OpenCV)
- Checksum builder (MD5)
- Integrity verifier
- Encryption tools

LoRa implementation using:
- Adafruit CircuitPython RFM9x library
- Python pyserial library

---

## Quick Reference

**Start Receiver (Windows):**
```bash
python lora_receive.py
```

**Start Transmission (Pi):**
```bash
python3 workflow.py --auto-mount
```

**Verify Files (Windows):**
```bash
cd IntegrityVerifier
python verify_manifest.py ../received_images
```

Done! 🎉
