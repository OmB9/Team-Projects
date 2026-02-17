#!/usr/bin/env python3
"""
LoRa USB Dongle Tester
Helps identify what type of dongle you have and what protocol it uses
"""

import serial
import serial.tools.list_ports
import time
import sys


def list_ports():
    """List all available COM ports"""
    print("\n" + "="*60)
    print("Available COM Ports:")
    print("="*60)
    
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No COM ports found!")
        return None
    
    for i, port in enumerate(ports, 1):
        print(f"\n{i}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
        
        # Try to identify LoRa-related keywords
        keywords = ['CP2102', 'CH340', 'FT232', 'USB SERIAL', 'RFM', 'LORA']
        desc_upper = port.description.upper()
        
        for keyword in keywords:
            if keyword in desc_upper:
                print(f"   *** Possible LoRa device (contains '{keyword}') ***")
    
    print("\n" + "="*60)
    return ports


def test_at_commands(ser):
    """Test if dongle responds to AT commands"""
    print("\n" + "="*60)
    print("Testing AT Commands:")
    print("="*60)
    
    at_commands = [
        "AT",
        "AT+MODE=?",
        "AT+ADDRESS=?",
        "AT+PARAMETER=?",
        "AT+VERSION",
        "AT+HELP"
    ]
    
    responded = False
    
    for cmd in at_commands:
        # Clear buffer
        ser.reset_input_buffer()
        
        # Send command
        ser.write((cmd + '\r\n').encode())
        time.sleep(0.2)
        
        # Read response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            if response.strip():
                print(f"\n  Sent: {cmd}")
                print(f"  Response: {response.strip()}")
                responded = True
    
    if responded:
        print("\n✓ Dongle appears to use AT commands!")
        print("  Type: AT Command Based")
        return "AT_COMMAND"
    else:
        print("\n✗ No response to AT commands")
        return None


def test_transparent_mode(ser, duration=10):
    """Listen for raw data (transparent mode)"""
    print("\n" + "="*60)
    print(f"Testing Transparent Mode (listening for {duration} seconds):")
    print("="*60)
    print("\n⚠ Make sure Raspberry Pi is transmitting now!")
    print("  Starting in 3 seconds...\n")
    
    time.sleep(3)
    
    start = time.time()
    received_any = False
    packet_count = 0
    
    print("Listening...\n")
    
    while time.time() - start < duration:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            received_any = True
            packet_count += 1
            
            print(f"Packet {packet_count} ({len(data)} bytes):")
            print(f"  Hex: {data.hex()}")
            
            # Try to decode as ASCII
            ascii_str = data.decode('utf-8', errors='replace')
            printable = ''.join(c if c.isprintable() else '.' for c in ascii_str)
            print(f"  ASCII: {printable}")
            
            # Check for common patterns
            if data[0:1] == b'\xAA':
                print("  ⚠ Starts with 0xAA - might use packet markers")
            if b'+RCV=' in data:
                print("  ⚠ Contains '+RCV=' - AT command format")
            
            print()
        
        time.sleep(0.1)
    
    if received_any:
        print(f"\n✓ Received {packet_count} packet(s)!")
        print("  Type: Transparent or Custom Protocol")
        return "TRANSPARENT"
    else:
        print("\n✗ No data received")
        print("\nPossible issues:")
        print("  - Pi not transmitting")
        print("  - Wrong COM port")
        print("  - Wrong baudrate")
        print("  - Antenna not connected")
        print("  - Wrong frequency (Pi=915MHz, Dongle=915MHz?)")
        return None


def analyze_protocol(ser):
    """Comprehensive protocol analysis"""
    print("\n\n" + "#"*60)
    print("# Protocol Analysis")
    print("#"*60)
    
    # Test 1: AT Commands
    protocol = test_at_commands(ser)
    
    if protocol == "AT_COMMAND":
        return protocol
    
    # Test 2: Transparent mode
    protocol = test_transparent_mode(ser)
    
    return protocol


def provide_recommendations(protocol):
    """Provide next steps based on detected protocol"""
    print("\n\n" + "#"*60)
    print("# Recommendations")
    print("#"*60)
    
    if protocol == "AT_COMMAND":
        print("""
✓ Your dongle uses AT commands

Next steps:
1. Review WINDOWS_DONGLE_GUIDE.md - "For AT Command Dongles" section
2. Modify lora_receive.py to use AT command format
3. Or use the provided AT command receiver template

Example configuration:
  AT+MODE=0           # Receive mode
  AT+ADDRESS=0        # Device address
  AT+NETWORKID=0      # Network ID
  AT+PARAMETER=7,7,1,7  # Match Pi settings (SF7, BW250, CR5)

Common AT command dongles:
  - Reyax RYLR896
  - Ebyte E32 series
  - HC-12 LoRa modules
        """)
    
    elif protocol == "TRANSPARENT":
        print("""
✓ Your dongle appears to use transparent mode

Next steps:
1. Your current lora_receive.py should work!
2. Run: python lora_receive.py -p COMx
3. Start Pi transmission
4. Images should be received automatically

If still having issues:
  - Check that received hex data matches packet format (see LORA_SETUP.md)
  - Verify 915MHz frequency on both ends
  - Ensure antennas are connected
        """)
    
    else:
        print("""
✗ Could not determine protocol

Troubleshooting steps:

1. Verify hardware connections:
   ✓ Antenna connected to dongle?
   ✓ Dongle plugged into USB?
   ✓ Driver installed (check Device Manager)?

2. Verify Pi is transmitting:
   ✓ Run lora_transmit.py on Pi
   ✓ Check for transmission messages
   ✓ Verify Adafruit bonnet is seated properly

3. Check frequency match:
   ✓ Both must be 915MHz
   ✓ Check dongle specifications

4. Try different baudrates:
   Common: 9600, 19200, 38400, 57600, 115200
   Rerun this test with: python test_dongle.py -b <baudrate>

5. Alternative: Use second Raspberry Pi as receiver
   (Easier than debugging unknown USB protocol!)

6. Contact support with:
   - Dongle model/brand
   - Output from this test
   - Photo of dongle/label
        """)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test and identify LoRa USB dongle type"
    )
    parser.add_argument(
        "-p", "--port",
        help="COM port (e.g., COM3). Will prompt if not specified"
    )
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)"
    )
    parser.add_argument(
        "-t", "--test-duration",
        type=int,
        default=10,
        help="Transparent mode test duration in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "#"*60)
    print("# LoRa USB Dongle Tester")
    print("#"*60)
    
    # List available ports
    ports = list_ports()
    
    if not ports:
        print("\nNo COM ports found. Check:")
        print("  1. Dongle is plugged in")
        print("  2. Driver is installed")
        print("  3. Device Manager shows the device")
        return
    
    # Select port
    if args.port:
        port = args.port
    else:
        print("\nEnter COM port number (e.g., 3 for COM3)")
        while True:
            try:
                choice = input("Port number: ").strip()
                if choice.upper().startswith("COM"):
                    port = choice.upper()
                else:
                    port = f"COM{choice}"
                break
            except KeyboardInterrupt:
                print("\n\nCancelled")
                return
    
    # Connect
    print(f"\n{'='*60}")
    print(f"Connecting to {port} at {args.baudrate} baud...")
    print("="*60)
    
    try:
        ser = serial.Serial(port, args.baudrate, timeout=1)
        time.sleep(2)  # Wait for connection to stabilize
        print(f"✓ Connected to {port}")
        
        # Run analysis
        protocol = analyze_protocol(ser)
        
        # Provide recommendations
        provide_recommendations(protocol)
        
        # Close connection
        ser.close()
        print("\n✓ Test complete\n")
        
    except serial.SerialException as e:
        print(f"\n✗ Error: {e}")
        print("\nCommon issues:")
        print("  - Wrong COM port number")
        print("  - Port already in use (close other programs)")
        print("  - Driver not installed")
        print("  - Insufficient permissions")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        try:
            ser.close()
        except:
            pass


if __name__ == "__main__":
    main()
