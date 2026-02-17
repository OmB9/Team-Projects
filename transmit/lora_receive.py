#!/usr/bin/env python3
"""
LoRa Image Receiver for Windows
Receives images transmitted via LoRa from Raspberry Pi
"""

import serial
import serial.tools.list_ports
import struct
import time
from pathlib import Path
from collections import defaultdict

# Packet Configuration (must match transmitter)
MAX_PAYLOAD = 250
HEADER_SIZE = 10

# Packet Types
PKT_FILE_START = 0x01
PKT_FILE_DATA = 0x02
PKT_FILE_END = 0x03
PKT_MANIFEST = 0x04
PKT_ACK_REQUEST = 0x05


class LoRaReceiver:
    def __init__(self, port=None, baudrate=115200):
        """
        Initialize the LoRa receiver
        
        Args:
            port: COM port (e.g., 'COM3'). If None, will auto-detect
            baudrate: Serial baudrate (default 115200)
        """
        if port is None:
            port = self.find_lora_port()
            if port is None:
                raise Exception("No LoRa device found. Please specify COM port manually.")
        
        self.port = port
        self.serial = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Wait for serial to initialize
        
        print(f"LoRa Receiver initialized on {port}")
        print(f"Baudrate: {baudrate}")
        print("Waiting for transmissions...\n")
        
        # File reassembly buffers
        self.files = defaultdict(lambda: {
            'filename': None,
            'packets': {},
            'total_packets': 0,
            'received_packets': 0
        })
        
        self.manifest_packets = {}
        self.manifest_total = 0
        
        # Statistics
        self.stats = {
            'packets_received': 0,
            'packets_failed': 0,
            'files_completed': 0
        }
    
    def find_lora_port(self):
        """Auto-detect LoRa USB device"""
        print("Scanning for LoRa devices...")
        
        ports = serial.tools.list_ports.comports()
        
        # Common LoRa device identifiers
        lora_keywords = ['CP2102', 'CH340', 'FT232', 'USB Serial', 'RFM']
        
        for port in ports:
            desc = port.description.upper()
            for keyword in lora_keywords:
                if keyword.upper() in desc:
                    print(f"Found potential LoRa device: {port.device} - {port.description}")
                    return port.device
        
        print("\nAvailable COM ports:")
        for port in ports:
            print(f"  {port.device}: {port.description}")
        
        return None
    
    def crc16(self, data):
        """Calculate CRC16 checksum (must match transmitter)"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def parse_packet(self, packet):
        """
        Parse packet header and data
        
        Returns:
            Tuple of (packet_type, file_id, packet_num, total_packets, data) or None if invalid
        """
        if len(packet) < HEADER_SIZE:
            return None
        
        try:
            # Parse header
            header = struct.unpack('>BBHHHHH', packet[:HEADER_SIZE])
            packet_type = header[0]
            file_id = header[1]
            packet_num = header[2]
            total_packets = header[3]
            data_len = header[4]
            expected_checksum = header[5]
            
            # Extract data
            data = packet[HEADER_SIZE:HEADER_SIZE + data_len]
            
            # Verify checksum
            actual_checksum = self.crc16(data)
            if actual_checksum != expected_checksum:
                print(f"  ⚠ Checksum mismatch! Expected {expected_checksum:04x}, got {actual_checksum:04x}")
                return None
            
            return packet_type, file_id, packet_num, total_packets, data
            
        except struct.error as e:
            print(f"  ⚠ Packet parse error: {e}")
            return None
    
    def handle_file_start(self, file_id, total_packets, data):
        """Handle FILE_START packet"""
        filename = data.decode('utf-8', errors='ignore')
        
        self.files[file_id]['filename'] = filename
        self.files[file_id]['total_packets'] = total_packets
        self.files[file_id]['packets'] = {}
        self.files[file_id]['received_packets'] = 0
        
        print(f"\n{'='*60}")
        print(f"📥 Starting file: {filename}")
        print(f"   File ID: {file_id}")
        print(f"   Total packets: {total_packets}")
        print(f"{'='*60}")
    
    def handle_file_data(self, file_id, packet_num, total_packets, data):
        """Handle FILE_DATA packet"""
        if file_id not in self.files:
            print(f"  ⚠ Received data for unknown file ID {file_id}")
            return
        
        # Store packet
        self.files[file_id]['packets'][packet_num] = data
        self.files[file_id]['received_packets'] += 1
        
        received = self.files[file_id]['received_packets']
        total = self.files[file_id]['total_packets']
        
        print(f"  📦 Packet {packet_num + 1}/{total} ({len(data)} bytes) - Progress: {received}/{total}")
    
    def handle_file_end(self, file_id, output_dir='received_images'):
        """Handle FILE_END packet and save the file"""
        if file_id not in self.files:
            print(f"  ⚠ Received END for unknown file ID {file_id}")
            return
        
        file_info = self.files[file_id]
        
        # Check if we have all packets
        if file_info['received_packets'] != file_info['total_packets']:
            print(f"  ⚠ Missing packets! Received {file_info['received_packets']}/{file_info['total_packets']}")
            return
        
        # Reassemble file
        print(f"\n  🔧 Reassembling file...")
        
        file_data = b''
        for packet_num in sorted(file_info['packets'].keys()):
            file_data += file_info['packets'][packet_num]
        
        # Save file
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        file_path = output_path / file_info['filename']
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        print(f"  ✓ File saved: {file_path}")
        print(f"  ✓ Size: {len(file_data):,} bytes")
        print(f"{'='*60}\n")
        
        self.stats['files_completed'] += 1
        
        # Clean up
        del self.files[file_id]
    
    def handle_manifest(self, packet_num, total_packets, data):
        """Handle MANIFEST packet"""
        self.manifest_packets[packet_num] = data
        self.manifest_total = total_packets
        
        print(f"  📋 Manifest packet {packet_num + 1}/{total_packets}")
        
        # Check if manifest is complete
        if len(self.manifest_packets) == total_packets:
            self.save_manifest()
    
    def save_manifest(self, output_dir='received_images'):
        """Save the complete manifest file"""
        print(f"\n{'='*60}")
        print(f"📋 Saving manifest...")
        
        # Reassemble manifest
        manifest_data = b''
        for packet_num in sorted(self.manifest_packets.keys()):
            manifest_data += self.manifest_packets[packet_num]
        
        # Save manifest
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        manifest_path = output_path / "manifest.md5"
        
        with open(manifest_path, 'wb') as f:
            f.write(manifest_data)
        
        print(f"✓ Manifest saved: {manifest_path}")
        print(f"✓ Size: {len(manifest_data)} bytes")
        print(f"{'='*60}\n")
    
    def receive_packet(self):
        """
        Receive and process one packet
        
        Returns:
            True if packet received, False if timeout
        """
        try:
            # Read packet (implementation depends on your USB dongle)
            # Most LoRa USB dongles use AT commands or binary protocol
            
            # Example for simple binary protocol:
            # Wait for start marker or data
            if self.serial.in_waiting > 0:
                # Read available data
                packet = self.serial.read(self.serial.in_waiting)
                
                if len(packet) == 0:
                    return False
                
                self.stats['packets_received'] += 1
                
                # Parse packet
                parsed = self.parse_packet(packet)
                
                if parsed is None:
                    self.stats['packets_failed'] += 1
                    return False
                
                packet_type, file_id, packet_num, total_packets, data = parsed
                
                # Handle different packet types
                if packet_type == PKT_FILE_START:
                    self.handle_file_start(file_id, total_packets, data)
                
                elif packet_type == PKT_FILE_DATA:
                    self.handle_file_data(file_id, packet_num, total_packets, data)
                
                elif packet_type == PKT_FILE_END:
                    self.handle_file_end(file_id)
                
                elif packet_type == PKT_MANIFEST:
                    self.handle_manifest(packet_num, total_packets, data)
                
                return True
            
            return False
            
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            return False
        except Exception as e:
            print(f"Error receiving packet: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def listen(self, timeout=None):
        """
        Listen for incoming transmissions
        
        Args:
            timeout: Optional timeout in seconds. None = listen forever
        """
        print(f"\n{'#'*60}")
        print(f"# LoRa Receiver Active")
        print(f"# Press Ctrl+C to stop")
        print(f"{'#'*60}\n")
        
        start_time = time.time()
        last_activity = time.time()
        
        try:
            while True:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    print(f"\nTimeout reached ({timeout}s)")
                    break
                
                # Receive packet
                if self.receive_packet():
                    last_activity = time.time()
                else:
                    time.sleep(0.1)
                
                # Show idle message every 10 seconds
                if time.time() - last_activity > 10:
                    elapsed = int(time.time() - last_activity)
                    print(f"  Waiting for transmission... ({elapsed}s idle)", end='\r')
        
        except KeyboardInterrupt:
            print("\n\nStopped by user")
        
        finally:
            self.print_statistics()
    
    def print_statistics(self):
        """Print reception statistics"""
        print(f"\n{'='*60}")
        print(f"Reception Statistics:")
        print(f"  Packets received: {self.stats['packets_received']}")
        print(f"  Packets failed: {self.stats['packets_failed']}")
        print(f"  Files completed: {self.stats['files_completed']}")
        
        if self.stats['packets_received'] > 0:
            success_rate = ((self.stats['packets_received'] - self.stats['packets_failed']) 
                           / self.stats['packets_received'] * 100)
            print(f"  Success rate: {success_rate:.1f}%")
        
        print(f"{'='*60}")
    
    def close(self):
        """Close serial connection"""
        if self.serial.is_open:
            self.serial.close()
            print("Serial connection closed")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Receive images via LoRa")
    parser.add_argument(
        "-p", "--port",
        help="COM port (e.g., COM3). Auto-detect if not specified"
    )
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)"
    )
    parser.add_argument(
        "-o", "--output",
        default="received_images",
        help="Output directory (default: received_images)"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        help="Reception timeout in seconds (default: none)"
    )
    
    args = parser.parse_args()
    
    try:
        receiver = LoRaReceiver(port=args.port, baudrate=args.baudrate)
        receiver.listen(timeout=args.timeout)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            receiver.close()
        except:
            pass


if __name__ == "__main__":
    main()
