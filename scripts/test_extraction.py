#!/usr/bin/env python3
"""
Test script to verify OpenAI image extraction is working correctly.

Usage:
    python scripts/test_extraction.py [image_path1] [image_path2] ...

If no images are provided, it will look for test images in tests/sample_images/
or prompt you to provide paths.

Example:
    python scripts/test_extraction.py ~/Desktop/cycling_screenshot.jpg ~/Desktop/sleep.png
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Set up logging to see extraction details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from models.services.openai_extraction import (
    extract_from_image,
    extract_batch,
    CyclingWorkoutPayload,
    SleepSummaryPayload,
    UnknownPayload
)


def test_single_image(image_path: str) -> None:
    """Test extraction from a single image"""
    print(f"\n{'='*60}")
    print(f"Testing: {image_path}")
    print('='*60)
    
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return
    
    filename = os.path.basename(image_path)
    
    with open(image_path, 'rb') as f:
        payload = extract_from_image(f, filename)
    
    print(f"\n📋 RESULT:")
    print(f"   Type: {payload.type}")
    
    if isinstance(payload, CyclingWorkoutPayload):
        print(f"   ✅ Classified as CYCLING WORKOUT")
        print(f"   📅 Date: {payload.workout_date or 'N/A'}")
        print(f"   ⏱️  Duration: {payload.duration_sec}s" if payload.duration_sec else "   ⏱️  Duration: N/A")
        print(f"   ⚡ Avg Power: {payload.avg_power_w}W" if payload.avg_power_w else "   ⚡ Avg Power: N/A")
        print(f"   ⚡ Max Power: {payload.max_power_w}W" if payload.max_power_w else "   ⚡ Max Power: N/A")
        print(f"   ❤️  Avg HR: {payload.avg_heart_rate} BPM" if payload.avg_heart_rate else "   ❤️  Avg HR: N/A")
        print(f"   ❤️  Max HR: {payload.max_heart_rate} BPM" if payload.max_heart_rate else "   ❤️  Max HR: N/A")
        print(f"   🔄 Avg Cadence: {payload.avg_cadence} RPM" if payload.avg_cadence else "   🔄 Avg Cadence: N/A")
        print(f"   📏 Distance: {payload.distance_km} km" if payload.distance_km else "   📏 Distance: N/A")
        print(f"   📊 TSS: {payload.tss}" if payload.tss else "   📊 TSS: N/A")
        print(f"   🔥 Calories: {payload.kcal_total}" if payload.kcal_total else "   🔥 Calories: N/A")
        
    elif isinstance(payload, SleepSummaryPayload):
        print(f"   ✅ Classified as SLEEP SUMMARY")
        print(f"   📅 Date: {payload.sleep_end_date or 'N/A'}")
        print(f"   😴 Total Sleep: {payload.total_sleep_minutes} min" if payload.total_sleep_minutes else "   😴 Total Sleep: N/A")
        print(f"   🌙 Deep Sleep: {payload.deep_sleep_minutes} min" if payload.deep_sleep_minutes else "   🌙 Deep Sleep: N/A")
        print(f"   💭 REM: {payload.rem_minutes} min" if payload.rem_minutes else "   💭 REM: N/A")
        print(f"   🔔 Wakeups: {payload.wakeups_count}" if payload.wakeups_count else "   🔔 Wakeups: N/A")
        print(f"   ❤️  Min HR: {payload.min_heart_rate} BPM" if payload.min_heart_rate else "   ❤️  Min HR: N/A")
        
    elif isinstance(payload, UnknownPayload):
        print(f"   ⚠️  Classified as UNKNOWN")
        print(f"   Notes: {payload.notes}")
    
    return payload


def test_batch_extraction(image_paths: list) -> None:
    """Test batch extraction from multiple images"""
    print(f"\n{'='*60}")
    print(f"Testing BATCH extraction with {len(image_paths)} images")
    print('='*60)
    
    # Prepare images
    images = []
    for path in image_paths:
        if not os.path.exists(path):
            print(f"⚠️  Skipping (not found): {path}")
            continue
        with open(path, 'rb') as f:
            # Read file content (need to keep it in memory for batch)
            from io import BytesIO
            content = BytesIO(f.read())
            images.append((content, os.path.basename(path)))
    
    if not images:
        print("❌ No valid images to process")
        return
    
    result = extract_batch(images)
    
    print(f"\n📋 BATCH RESULT:")
    print(f"   Images processed: {len(result.image_results)}")
    
    print(f"\n   Per-image results:")
    for img_result in result.image_results:
        print(f"   - {img_result.filename}: {img_result.type} (confidence: {img_result.confidence:.2f})")
    
    if result.canonical_workout.date:
        print(f"\n   📊 Canonical Workout:")
        cw = result.canonical_workout
        print(f"      Date: {cw.date}")
        print(f"      Duration: {cw.duration_minutes} min" if cw.duration_minutes else "      Duration: N/A")
        print(f"      Avg Power: {cw.avg_power}W" if cw.avg_power else "      Avg Power: N/A")
        print(f"      Avg HR: {cw.avg_hr} BPM" if cw.avg_hr else "      Avg HR: N/A")
    
    if result.canonical_sleep.date:
        print(f"\n   😴 Canonical Sleep:")
        cs = result.canonical_sleep
        print(f"      Date: {cs.date}")
        print(f"      Total: {cs.total_sleep_minutes} min" if cs.total_sleep_minutes else "      Total: N/A")
    
    if result.missing_fields.get('workout') or result.missing_fields.get('sleep'):
        print(f"\n   ⚠️  Missing fields: {result.missing_fields}")
    
    if result.errors:
        print(f"\n   ❌ Errors: {result.errors}")


def main():
    print("\n" + "="*60)
    print("🚴 Zyra Cycle - Image Extraction Test")
    print("="*60)
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("\n❌ ERROR: OPENAI_API_KEY not set in environment")
        print("   Please set it in your .env file or environment")
        sys.exit(1)
    
    # Get image paths from command line or use defaults
    if len(sys.argv) > 1:
        image_paths = sys.argv[1:]
    else:
        # Check for sample images
        sample_dir = os.path.join(project_root, 'tests', 'sample_images')
        if os.path.exists(sample_dir):
            image_paths = [
                os.path.join(sample_dir, f) 
                for f in os.listdir(sample_dir) 
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic'))
            ]
        else:
            print("\n📁 No sample images found in tests/sample_images/")
            print("   Please provide image paths as arguments:")
            print("   python scripts/test_extraction.py image1.jpg image2.png")
            sys.exit(0)
    
    if not image_paths:
        print("\n❌ No images provided")
        print("   Usage: python scripts/test_extraction.py image1.jpg image2.png")
        sys.exit(1)
    
    print(f"\n📸 Testing {len(image_paths)} image(s)...")
    
    # Test each image individually
    results = []
    for path in image_paths:
        result = test_single_image(path)
        if result:
            results.append((path, result))
    
    # If multiple images, also test batch extraction
    if len(image_paths) > 1:
        test_batch_extraction(image_paths)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    cycling_count = sum(1 for _, r in results if isinstance(r, CyclingWorkoutPayload))
    sleep_count = sum(1 for _, r in results if isinstance(r, SleepSummaryPayload))
    unknown_count = sum(1 for _, r in results if isinstance(r, UnknownPayload))
    
    print(f"   Total images: {len(results)}")
    print(f"   🚴 Cycling workouts: {cycling_count}")
    print(f"   😴 Sleep summaries: {sleep_count}")
    print(f"   ❓ Unknown: {unknown_count}")
    
    if unknown_count > 0:
        print(f"\n   ⚠️  {unknown_count} image(s) were not recognized.")
        print("   Check the logs above for details.")
    
    if cycling_count > 0:
        print(f"\n   ✅ Cycling extraction is working!")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    main()

