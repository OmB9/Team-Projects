#!/usr/bin/env python3
"""
Complete Workflow: USB Images -> Red Circle Detection -> LoRa Transmission

This script orchestrates the entire process:
1. Mount USB drive (if needed)
2. Detect images with red circles
3. Create manifest with checksums
4. Transmit via LoRa

Usage:
    python workflow.py /media/usb0/images
    python workflow.py --auto-mount
"""

import subprocess
import sys
from pathlib import Path
import time
import shutil

class WorkflowManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.working_dir = self.project_root / "working"
        self.output_dir = self.working_dir / "with_red_circles"
        
    def check_dependencies(self):
        """Check if required scripts and dependencies exist"""
        print("Checking dependencies...")
        
        required_files = [
            "ImageSorting/sort.py",
            "ChecksumBuilder/make_manifest.py",
            "lora_transmit.py"
        ]
        
        missing = []
        for file in required_files:
            if not (self.project_root / file).exists():
                missing.append(file)
        
        if missing:
            print(f"❌ Missing required files:")
            for file in missing:
                print(f"   - {file}")
            return False
        
        # Check Python packages
        try:
            import cv2
            import numpy as np
            import board
            import adafruit_rfm9x
        except ImportError as e:
            print(f"❌ Missing Python package: {e}")
            print("\nInstall with:")
            print("  pip install opencv-python numpy --break-system-packages")
            print("  pip install adafruit-circuitpython-rfm9x --break-system-packages")
            return False
        
        print("✓ All dependencies found\n")
        return True
    
    def find_usb_drive(self):
        """Find mounted USB drive"""
        print("Looking for USB drive...")
        
        # Common mount points
        mount_points = [
            Path("/media/pi"),
            Path("/media"),
            Path("/mnt")
        ]
        
        for mount_point in mount_points:
            if mount_point.exists():
                for item in mount_point.iterdir():
                    if item.is_dir():
                        print(f"Found potential USB: {item}")
                        return item
        
        return None
    
    def detect_red_circles(self, input_dir):
        """Run red circle detection"""
        print(f"\n{'='*60}")
        print("STEP 1: Detecting images with red circles")
        print(f"{'='*60}\n")
        
        sort_script = self.project_root / "ImageSorting" / "sort.py"
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run sort.py
        cmd = [
            sys.executable,
            str(sort_script),
            str(input_dir),
            "-o", str(self.output_dir)
        ]
        
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode != 0:
            print("❌ Red circle detection failed")
            return False
        
        # Check how many images were found
        images = list(self.output_dir.glob("*.png"))
        
        if len(images) == 0:
            print("❌ No images with red circles found!")
            return False
        
        print(f"\n✓ Found {len(images)} images with red circles")
        
        # Limit to 10 images for the project requirement
        if len(images) > 10:
            print(f"\n⚠ Found {len(images)} images, but project requires 10")
            print("Keeping the first 10 images...")
            
            for img in sorted(images)[10:]:
                img.unlink()
            
            images = list(self.output_dir.glob("*.png"))
        
        print(f"Selected {len(images)} images for transmission\n")
        return True
    
    def create_manifest(self):
        """Create MD5 manifest"""
        print(f"\n{'='*60}")
        print("STEP 2: Creating checksum manifest")
        print(f"{'='*60}\n")
        
        manifest_script = self.project_root / "ChecksumBuilder" / "make_manifest.py"
        
        cmd = [
            sys.executable,
            str(manifest_script),
            str(self.output_dir)
        ]
        
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode != 0:
            print("❌ Manifest creation failed")
            return False
        
        manifest_path = self.output_dir / "manifest.md5"
        if not manifest_path.exists():
            print("❌ Manifest file not created")
            return False
        
        print(f"\n✓ Manifest created: {manifest_path}\n")
        return True
    
    def transmit_via_lora(self):
        """Transmit images via LoRa"""
        print(f"\n{'='*60}")
        print("STEP 3: Transmitting via LoRa")
        print(f"{'='*60}\n")
        
        transmit_script = self.project_root / "lora_transmit.py"
        
        cmd = [
            sys.executable,
            str(transmit_script),
            str(self.output_dir)
        ]
        
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode != 0:
            print("❌ LoRa transmission failed")
            return False
        
        print(f"\n✓ Transmission complete\n")
        return True
    
    def run(self, input_dir=None, auto_mount=False):
        """Run the complete workflow"""
        print(f"\n{'#'*60}")
        print("# Complete Image Processing & Transmission Workflow")
        print(f"{'#'*60}\n")
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Find input directory
        if auto_mount:
            input_dir = self.find_usb_drive()
            if input_dir is None:
                print("❌ No USB drive found")
                return False
        elif input_dir is None:
            print("❌ No input directory specified")
            print("Usage: python workflow.py <input_dir>")
            print("   or: python workflow.py --auto-mount")
            return False
        else:
            input_dir = Path(input_dir)
            if not input_dir.exists():
                print(f"❌ Input directory not found: {input_dir}")
                return False
        
        print(f"Input directory: {input_dir}\n")
        
        # Run workflow steps
        try:
            # Step 1: Detect red circles
            if not self.detect_red_circles(input_dir):
                return False
            
            # Step 2: Create manifest
            if not self.create_manifest():
                return False
            
            # Step 3: Transmit via LoRa
            print("\n⚠ Make sure Windows receiver is running!")
            print("Press Enter to start transmission, or Ctrl+C to cancel...")
            input()
            
            if not self.transmit_via_lora():
                return False
            
            print(f"\n{'#'*60}")
            print("# ✓ WORKFLOW COMPLETE!")
            print(f"{'#'*60}\n")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n❌ Workflow interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Complete workflow: Detect images with red circles and transmit via LoRa"
    )
    parser.add_argument(
        "input_dir",
        nargs='?',
        help="Directory containing input images (e.g., /media/usb0/images)"
    )
    parser.add_argument(
        "--auto-mount",
        action="store_true",
        help="Automatically find and use USB drive"
    )
    
    args = parser.parse_args()
    
    workflow = WorkflowManager()
    success = workflow.run(args.input_dir, args.auto_mount)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
