# Windows LoRa USB Dongle Configuration Guide

## Problem: Generic Implementation

The `lora_receive.py` script currently has a generic serial receiver that may need adaptation for your specific USB dongle. Most LoRa USB dongles use one of several protocols.

---

## Common LoRa USB Dongle Types

### Type 1: Transparent Serial Bridge (Simplest)
- RFM95W module + USB-to-serial chip
- Data passes through transparently
- **No special protocol needed**
- Works with current implementation ✓

### Type 2: AT Command Based
- Requires AT commands to configure and receive
- Examples: Reyax RYLR896, E32-TTL-1W
- **Needs modification** (see below)

### Type 3: Custom Protocol
- Has specific packet framing
- May use START/END markers
- **Needs modification** (see below)

---

## How to Identify Your Dongle Type

### Method 1: Test with Serial Terminal

**Windows:**
```bash
# Install PuTTY or use Arduino Serial Monitor
# Connect to your COM port at 115200 baud

# Try sending AT commands:
AT
AT+MODE=0
AT+ADDRESS=0
```

**If you get "OK" or similar response → Type 2 (AT commands)**
**If you get garbage or nothing → Type 1 (transparent) or Type 3**

### Method 2: Check Manufacturer Documentation

Look for:
- Product datasheet
- User manual
- Arduino example code
- GitHub repositories

Common brands:
- **Reyax**: Usually AT command
- **Ebyte (E32)**: Custom protocol
- **HopeRF**: Usually transparent
- **Adafruit**: Transparent or I2C

---

## Adaptation Guides

### For Transparent Serial (Type 1) - Current Implementation

**No changes needed!** Your current `lora_receive.py` should work as-is.

The dongle directly outputs received LoRa packets to the serial port.

### For AT Command Dongles (Type 2)

You need to:
1. Initialize with AT commands
2. Set receive mode
3. Parse AT response format

**Modified receive_packet() method:**

```python
def receive_packet(self):
    """Receive packet from AT command dongle"""
    try:
        # Read a line from serial
        if self.serial.in_waiting > 0:
            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            
            # Check for data receive command
            # Format usually: +RCV=<address>,<length>,<data>,<RSSI>,<SNR>
            if line.startswith('+RCV='):
                parts = line.split(',')
                if len(parts) >= 3:
                    # Extract hex data
                    hex_data = parts[2]
                    # Convert hex string to bytes
                    packet = bytes.fromhex(hex_data)
                    
                    # Parse packet (rest is same)
                    parsed = self.parse_packet(packet)
                    # ... continue with existing logic
                    
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False
```

**Initialization (add to __init__):**

```python
def __init__(self, port=None, baudrate=115200):
    # ... existing code ...
    
    # Initialize AT command dongle
    self.send_at_command("AT")  # Test
    self.send_at_command("AT+MODE=0")  # Set to receive mode
    self.send_at_command("AT+ADDRESS=0")  # Set address
    self.send_at_command("AT+NETWORKID=0")  # Set network ID
    
    print("AT command dongle initialized")

def send_at_command(self, cmd, wait_response=True):
    """Send AT command and wait for response"""
    self.serial.write((cmd + '\r\n').encode())
    
    if wait_response:
        time.sleep(0.1)
        response = self.serial.readline().decode('utf-8', errors='ignore')
        print(f"  {cmd} -> {response.strip()}")
        return response
```

### For Custom Protocol (Type 3)

**You need to determine:**
1. Start/end markers
2. Packet framing format
3. Length encoding

**Example for dongles using START/END markers:**

```python
def receive_packet(self):
    """Receive packet with START/END markers"""
    START_MARKER = 0xAA
    END_MARKER = 0x55
    
    buffer = bytearray()
    receiving = False
    
    while self.serial.in_waiting > 0:
        byte = self.serial.read(1)[0]
        
        if byte == START_MARKER:
            buffer = bytearray()
            receiving = True
        elif byte == END_MARKER and receiving:
            # Got complete packet
            packet = bytes(buffer)
            
            # Parse packet (rest is same)
            parsed = self.parse_packet(packet)
            # ... continue with existing logic
            
            return True
        elif receiving:
            buffer.append(byte)
    
    return False
```

---

## Quick Adaptation Template

**If you can provide:**
1. Your dongle's product name/model number
2. Any documentation or example code
3. Output from serial terminal test

**I can provide specific adaptation code.**

---

## Testing Your Dongle

### Test Script

Save as `test_dongle.py`:

```python
import serial
import serial.tools.list_ports
import time

# Find your port
ports = serial.tools.list_ports.comports()
print("Available ports:")
for port in ports:
    print(f"  {port.device}: {port.description}")

# Connect
port = input("\nEnter COM port (e.g., COM3): ")
ser = serial.Serial(port, 115200, timeout=1)
time.sleep(2)

print(f"\nConnected to {port}")
print("Listening for 10 seconds...\n")

start = time.time()
while time.time() - start < 10:
    if ser.in_waiting > 0:
        data = ser.read(ser.in_waiting)
        print(f"Received ({len(data)} bytes):")
        print(f"  Hex: {data.hex()}")
        print(f"  ASCII: {data.decode('utf-8', errors='ignore')}")
        print()
    
    time.sleep(0.1)

ser.close()
print("Done!")
```

**Run this while someone transmits from the Pi:**
```bash
python test_dongle.py
```

This will show you exactly what format your dongle uses.

---

## Common Dongles & Their Settings

### Reyax RYLR896 (AT Command)
```
Baudrate: 115200
Commands:
  AT+MODE=0          # Receive mode
  AT+ADDRESS=0       # Device address
  AT+NETWORKID=0     # Network ID
  AT+PARAMETER=7,7,1,7  # SF, BW, CR, Preamble

Receive format: +RCV=0,11,48656C6C6F,-99,40
                       ^addr ^len ^data  ^RSSI ^SNR
```

### Ebyte E32 (Custom Protocol)
```
Baudrate: 9600 (default) or 115200
Mode: Set M0=0, M1=0 for transparent
Data: Raw bytes, no framing needed
```

### HopeRF RFM95W USB (Transparent)
```
Baudrate: 115200
Data: Direct LoRa packets (our current implementation)
```

---

## Making Your Dongle Work

### Option 1: Modify lora_receive.py

Based on test results, update the `receive_packet()` method.

### Option 2: Use Existing Arduino Code

Many dongles have Arduino examples:

```cpp
// If you find Arduino code like this:
LoRa.onReceive(onReceive);

void onReceive(int packetSize) {
  // Read packet
  while (LoRa.available()) {
    byte b = LoRa.read();
    // Process byte
  }
}
```

**You can adapt to Python:**
```python
def receive_packet(self):
    if self.serial.in_waiting > 0:
        packet = self.serial.read(self.serial.in_waiting)
        # Process packet
```

### Option 3: Fallback to Manual Transfer

If you can't get the Windows dongle working:

**Windows Receiver Alternative:**
1. Use another Raspberry Pi as receiver
2. Transfer files via USB/Network afterward
3. Or use WiFi direct (much faster!)

---

## Need Help?

**Provide this information:**

1. **Dongle details:**
   - Brand/model name
   - Product link if available
   - Any labels on the device

2. **Test results:**
   ```bash
   python test_dongle.py
   # Copy the output
   ```

3. **Device Manager info:**
   - Driver name
   - Hardware ID

**Then I can provide exact code for your dongle!**

---

## Alternative: Use Second Raspberry Pi as Receiver

**Easiest solution if Windows dongle is difficult:**

**Receiver Pi:**
```bash
# Use same lora_transmit.py but in receive mode
# Modify to call rfm9x.receive() instead of send()
```

**Pseudo-code:**
```python
while True:
    packet = rfm9x.receive(timeout=5)
    if packet is not None:
        # Process packet
        parsed = parse_packet(packet)
        # Save to file
```

This avoids USB dongle complications entirely!

---

## Quick Decision Tree

```
Do you have documentation for your USB dongle?
├─ YES → Follow manufacturer's protocol
│         → Adapt lora_receive.py accordingly
│
└─ NO → Run test_dongle.py and check output
        ├─ Readable ASCII with +RCV → AT command type
        │                             → Use AT command adaptation
        │
        ├─ Raw binary data → Transparent type
        │                     → Current implementation works!
        │
        ├─ Nothing received → Check:
        │                     ├─ Driver installed?
        │                     ├─ Correct COM port?
        │                     ├─ Antenna connected?
        │                     └─ Pi transmitting?
        │
        └─ Strange format → Custom protocol
                           → Need more analysis
                           → Consider second Pi as receiver
```

---

## Summary

**Your next steps:**

1. **Identify your dongle type:**
   ```bash
   python test_dongle.py
   ```

2. **Try current implementation first:**
   ```bash
   python lora_receive.py
   ```

3. **If it doesn't work:**
   - Check test results
   - Look up dongle model
   - Apply appropriate adaptation
   - OR use second Pi as receiver

4. **Report findings to get specific help!**

---

Most 915MHz USB dongles are **transparent** or **AT command** based. 
The current implementation handles transparent. 
If you need AT command adaptation, it's a quick modification.

**Bottom line: We can make it work once we know your dongle type!**
