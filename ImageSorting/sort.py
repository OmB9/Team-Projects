#!/usr/bin/env python3
"""
Red Circle Detection Script

Detects images containing red circles (both hand-drawn annotations and perfect geometric circles)
using OpenCV. Prints matching filenames and moves them to a separate folder.
"""

import cv2
import numpy as np
import os
import shutil
from pathlib import Path
import math


def create_red_mask(image):
    """
    Create a binary mask for red regions in the image.
    Red color spans two HSV ranges: 0-10 and 170-180 hue.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Lower red range (0-10 hue)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    
    # Upper red range (170-180 hue)
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    # Combine both red ranges
    red_mask = cv2.bitwise_or(mask1, mask2)
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    
    return red_mask


def calculate_circularity(contour):
    """
    Calculate circularity of a contour.
    Circularity = 4 * pi * area / perimeter^2
    Perfect circle has circularity of 1.0
    """
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    
    if perimeter == 0:
        return 0
    
    circularity = (4 * math.pi * area) / (perimeter ** 2)
    return circularity


def detect_annotation_circles(red_mask, min_area=500, circularity_threshold=0.4):
    """
    Detect hand-drawn/annotation style circles using contour analysis.
    
    Args:
        red_mask: Binary mask of red regions
        min_area: Minimum contour area to consider
        circularity_threshold: Minimum circularity value (0-1, lower for hand-drawn)
    
    Returns:
        List of detected circle contours
    """
    circles_found = []
    
    # Find contours in the red mask
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Skip small contours
        if area < min_area:
            continue
        
        circularity = calculate_circularity(contour)
        
        # Check if contour is circular enough
        # Lower threshold for hand-drawn circles which are less perfect
        if circularity >= circularity_threshold:
            circles_found.append(contour)
    
    return circles_found


def detect_hough_circles(red_mask, min_radius=20, max_radius=500):
    """
    Detect perfect geometric circles using HoughCircles.
    
    Args:
        red_mask: Binary mask of red regions
        min_radius: Minimum circle radius
        max_radius: Maximum circle radius
    
    Returns:
        Array of detected circles (x, y, radius) or None
    """
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(red_mask, (9, 9), 2)
    
    # Detect circles using Hough transform
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=min_radius,
        maxRadius=max_radius
    )
    
    return circles


def has_red_circles(image_path, min_area=500, circularity_threshold=0.4):
    """
    Check if an image contains red circles.
    
    Args:
        image_path: Path to the image file
        min_area: Minimum area for contour detection
        circularity_threshold: Minimum circularity for annotation circles
    
    Returns:
        Tuple of (has_circles: bool, annotation_count: int, hough_count: int)
    """
    # Read the image
    image = cv2.imread(str(image_path))
    
    if image is None:
        print(f"Warning: Could not read image: {image_path}")
        return False, 0, 0
    
    # Create red color mask
    red_mask = create_red_mask(image)
    
    # Check if there's enough red content to analyze
    red_pixel_count = cv2.countNonZero(red_mask)
    if red_pixel_count < min_area:
        return False, 0, 0
    
    # Detect annotation-style circles
    annotation_circles = detect_annotation_circles(red_mask, min_area, circularity_threshold)
    annotation_count = len(annotation_circles)
    
    # Detect perfect geometric circles
    hough_circles = detect_hough_circles(red_mask)
    hough_count = 0 if hough_circles is None else len(hough_circles[0])
    
    has_circles = annotation_count > 0 or hough_count > 0
    
    return has_circles, annotation_count, hough_count


def get_image_files(directory):
    """
    Get all image files from a directory.
    
    Args:
        directory: Path to the directory
    
    Returns:
        List of image file paths
    """
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.webp'}
    image_files = []
    
    directory = Path(directory)
    
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    return sorted(image_files)


def process_images(input_dir, output_dir=None):
    """
    Process all images in a directory, detect red circles, and move matching images.
    
    Args:
        input_dir: Directory containing images to process
        output_dir: Directory to move images with red circles (default: input_dir/with_red_circles)
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return
    
    # Set default output directory
    if output_dir is None:
        output_path = input_path / "with_red_circles"
    else:
        output_path = Path(output_dir)
    
    # Get all image files
    image_files = get_image_files(input_path)
    
    if not image_files:
        print(f"No image files found in: {input_dir}")
        return
    
    print(f"\nScanning {len(image_files)} images for red circles...\n")
    print("-" * 60)
    
    images_with_circles = []
    
    for image_path in image_files:
        has_circles, annotation_count, hough_count = has_red_circles(image_path)
        
        if has_circles:
            images_with_circles.append(image_path)
            print(f"✓ {image_path.name}")
            print(f"    Annotation circles: {annotation_count}, Geometric circles: {hough_count}")
    
    print("-" * 60)
    print(f"\nResults: {len(images_with_circles)}/{len(image_files)} images contain red circles\n")
    
    # Move matching images to output directory
    if images_with_circles:
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Moving images with red circles to: {output_path}\n")
        
        for image_path in images_with_circles:
            dest_path = output_path / image_path.name
            shutil.copy2(image_path, dest_path)
            print(f"  Copied: {image_path.name} -> {dest_path}")
        
        print(f"\n✓ Done! {len(images_with_circles)} images copied to {output_path}")
    else:
        print("No images with red circles found.")


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Detect images containing red circles using OpenCV"
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default="SampleImages",
        help="Directory containing images to process (default: SampleImages)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory for images with red circles (default: input_dir/with_red_circles)"
    )
    parser.add_argument(
        "--min-area",
        type=int,
        default=500,
        help="Minimum contour area to consider (default: 500)"
    )
    parser.add_argument(
        "--circularity",
        type=float,
        default=0.4,
        help="Minimum circularity threshold 0-1 (default: 0.4)"
    )
    
    args = parser.parse_args()
    
    # If input_dir is relative, make it relative to script location
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        script_dir = Path(__file__).parent
        input_dir = script_dir / input_dir
    
    process_images(input_dir, args.output)


if __name__ == "__main__":
    main()

