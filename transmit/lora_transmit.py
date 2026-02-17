#!/usr/bin/env python3
"""
LoRa Image Transmitter for Raspberry Pi
Sends images with red circles via LoRa to Windows receiver
"""

import time
import board
import busio
import digitalio
import adafruit_rfm9x
from pathlib import Path
import hashlib
import struct

# LoRa Configuration
RADIO_FREQ_MHZ = 915.0
CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Packet Configuration
MAX_PAYLOAD = 250  # RFM95W max payload size
HEADER_SIZE = 10   # packet_type(1) + file_id(1) + packet_num(2) + total_packets(2) + data_len(2) + checksum(2)

# Packet Types
PKT_FILE_START = 0x01
PKT_FILE_DATA = 0x02
PKT_FILE_END = 0x03
PKT_MANIFEST = 0x04
PKT_ACK_REQUEST = 0x05

class LoRaTransmitter:
    def __init__(self):
        """Initialize the LoRa radio"""
        self.rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
        
        # Configure for maximum speed at short range
        self.rfm9x.tx_power = 23  # Max power (not needed at 10ft but ensures reliability)
        self.rfm9x.spreading_factor = 7  # Fastest spreading factor
        self.rfm9x.signal_bandwidth = 250000  # Widest bandwidth = fastest
        self.rfm9x.coding_rate = 5  # Lowest error correction overhead
        
        print(f"LoRa Radio initialized at {RADIO_FREQ_MHZ} MHz")
        print(f"Expected data rate: ~5-10 kbps")
        
    def create_packet(self, packet_type, file_id, packet_num, total_packets, data):
        """
        Create a packet with header and data
        
        Header format (10 bytes):
        - packet_type: 1 byte
        - file_id: 1 byte (0-255)
        - packet_num: 2 bytes (current packet number)
        - total_packets: 2 bytes
        - data_len: 2 bytes
        - checksum: 2 bytes (CRC16 of data)
        """
        data_len = len(data)
        checksum = self.crc16(data)
        
        header = struct.pack(
            '>BBHHHHH',
            packet_type,
            file_id,
            packet_num,
            total_packets,
            data_len,
            checksum,
            0  # padding to make even
        )
        
        return header[:HEADER_SIZE] + data
    
    def crc16(self, data):
        """Calculate CRC16 checksum"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def send_packet(self, packet, retries=3):
        """Send a packet with retries"""
        for attempt in range(retries):
            try:
                self.rfm9x.send(packet)
                time.sleep(0.1)  # Small delay between packets
                return True
            except Exception as e:
                print(f"  Retry {attempt + 1}/{retries}: {e}")
                time.sleep(0.5)
        return False
    
    def send_file(self, file_path, file_id):
        """
        Send a file in chunks over LoRa
        
        Args:
            file_path: Path to the file
            file_id: Unique ID for this file (0-255)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return False
        
        # Read entire file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        file_size = len(file_data)
        filename = file_path.name
        
        print(f"\n{'='*60}")
        print(f"Transmitting: {filename}")
        print(f"Size: {file_size:,} bytes")
        
        # Calculate number of packets needed
        data_per_packet = MAX_PAYLOAD - HEADER_SIZE
        total_packets = (file_size + data_per_packet - 1) // data_per_packet
        
        print(f"Packets: {total_packets}")
        print(f"{'='*60}")
        
        # Send FILE_START packet with filename
        filename_bytes = filename.encode('utf-8')[:MAX_PAYLOAD - HEADER_SIZE]
        start_packet = self.create_packet(
            PKT_FILE_START,
            file_id,
            0,
            total_packets,
            filename_bytes
        )
        
        print(f"Sending START packet...")
        if not self.send_packet(start_packet):
            print("Failed to send START packet")
            return False
        
        time.sleep(0.5)  # Give receiver time to prepare
        
        # Send data packets
        for packet_num in range(total_packets):
            start_idx = packet_num * data_per_packet
            end_idx = min(start_idx + data_per_packet, file_size)
            chunk = file_data[start_idx:end_idx]
            
            data_packet = self.create_packet(
                PKT_FILE_DATA,
                file_id,
                packet_num,
                total_packets,
                chunk
            )
            
            print(f"Sending packet {packet_num + 1}/{total_packets} ({len(chunk)} bytes)...", end='')
            
            if self.send_packet(data_packet):
                print(" ✓")
            else:
                print(" ✗ FAILED")
                return False
            
            # Small delay to prevent overwhelming receiver
            time.sleep(0.2)
        
        # Send FILE_END packet
        end_packet = self.create_packet(
            PKT_FILE_END,
            file_id,
            total_packets,
            total_packets,
            b''
        )
        
        print(f"Sending END packet...")
        if not self.send_packet(end_packet):
            print("Failed to send END packet")
            return False
        
        print(f"✓ File transmitted successfully!\n")
        return True
    
    def send_manifest(self, manifest_path):
        """Send the manifest file"""
        manifest_path = Path(manifest_path)
        
        if not manifest_path.exists():
            print(f"Warning: Manifest not found: {manifest_path}")
            return False
        
        # Read manifest
        with open(manifest_path, 'r') as f:
            manifest_data = f.read().encode('utf-8')
        
        print(f"\nSending manifest ({len(manifest_data)} bytes)...")
        
        # Send manifest in one or more packets
        data_per_packet = MAX_PAYLOAD - HEADER_SIZE
        total_packets = (len(manifest_data) + data_per_packet - 1) // data_per_packet
        
        for packet_num in range(total_packets):
            start_idx = packet_num * data_per_packet
            end_idx = min(start_idx + data_per_packet, len(manifest_data))
            chunk = manifest_data[start_idx:end_idx]
            
            manifest_packet = self.create_packet(
                PKT_MANIFEST,
                255,  # Special ID for manifest
                packet_num,
                total_packets,
                chunk
            )
            
            if not self.send_packet(manifest_packet):
                print(f"Failed to send manifest packet {packet_num + 1}")
                return False
        
        print("✓ Manifest sent\n")
        return True
    
    def transmit_images(self, image_dir, manifest_path=None):
        """
        Transmit all images from a directory
        
        Args:
            image_dir: Directory containing images to transmit
            manifest_path: Optional path to manifest.md5 file
        """
        image_dir = Path(image_dir)
        
        if not image_dir.exists():
            print(f"Error: Directory not found: {image_dir}")
            return
        
        # Get all PNG images
        images = sorted([f for f in image_dir.iterdir() if f.suffix.lower() == '.png'])
        
        if not images:
            print(f"No PNG images found in {image_dir}")
            return
        
        print(f"\n{'#'*60}")
        print(f"# LoRa Image Transmission")
        print(f"# Found {len(images)} images to transmit")
        print(f"{'#'*60}\n")
        
        # Transmit each image
        for file_id, image_path in enumerate(images):
            success = self.send_file(image_path, file_id)
            
            if not success:
                print(f"\n⚠ Transmission failed for {image_path.name}")
                user_input = input("Continue with next file? (y/n): ")
                if user_input.lower() != 'y':
                    break
            
            # Delay between files
            time.sleep(1)
        
        # Send manifest if provided
        if manifest_path:
            self.send_manifest(manifest_path)
        elif (image_dir / "manifest.md5").exists():
            self.send_manifest(image_dir / "manifest.md5")
        
        print(f"\n{'#'*60}")
        print(f"# Transmission Complete!")
        print(f"{'#'*60}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transmit images via LoRa")
    parser.add_argument(
        "image_dir",
        nargs='?',
        default="with_red_circles",
        help="Directory containing images (default: with_red_circles)"
    )
    parser.add_argument(
        "-m", "--manifest",
        help="Path to manifest.md5 file"
    )
    
    args = parser.parse_args()
    
    try:
        transmitter = LoRaTransmitter()
        transmitter.transmit_images(args.image_dir, args.manifest)
        
    except KeyboardInterrupt:
        print("\n\nTransmission interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
