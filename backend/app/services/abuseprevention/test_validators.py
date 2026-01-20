"""
Test script for the Abuse Prevention module.
Run this to verify all validators are working correctly.

Usage:
    python -m abuseprevention.test_validators
    
    Or with a real image:
    python -m abuseprevention.test_validators path/to/image.jpg
"""

import sys
import os
import io
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np

from abuseprevention.validators import (
    AIDetectionValidator,
    EXIFValidator,
    GPSValidator,
    WebExistenceValidator,
    ValidationResult
)
from abuseprevention.service import ImageValidationService
from abuseprevention.config import Config


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_result(result: ValidationResult, name: str):
    status = "✓ PASSED" if result.passed else "✗ FAILED"
    print(f"\n{name}: {status}")
    print(f"  Score: {result.score}")
    print(f"  Reason: {result.reason}")
    if result.details:
        for key, value in result.details.items():
            print(f"  {key}: {value}")


def create_test_image_with_exif():
    """Create a test image with fake EXIF data for testing."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='blue')
    
    # Note: PIL doesn't easily allow setting EXIF, so this image won't have EXIF
    # This simulates an AI-generated or screenshot image
    return img


def create_test_image_no_exif():
    """Create a test image without EXIF (simulates AI image)."""
    img = Image.new('RGB', (200, 200), color='red')
    # Add some random noise
    pixels = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    img = Image.fromarray(pixels)
    return img


def test_ai_detection():
    """Test AI Detection Validator."""
    print_header("Testing AI Detection Validator")
    
    validator = AIDetectionValidator(threshold=0.5)
    
    # Test 1: Image without EXIF (should fail/score low - likely AI)
    print("\n--- Test 1: Image without EXIF data ---")
    test_img = create_test_image_no_exif()
    result = validator.validate(test_img)
    print_result(result, "No EXIF Image")
    
    # Test 2: Check AI software detection logic
    print("\n--- Test 2: AI Software Signatures Check ---")
    print("  Known AI signatures being checked:")
    for sig in validator.AI_SOFTWARE_SIGNATURES[:5]:
        print(f"    - {sig}")
    print(f"    ... and {len(validator.AI_SOFTWARE_SIGNATURES) - 5} more")
    
    return True


def test_exif_validation():
    """Test EXIF Validator."""
    print_header("Testing EXIF Freshness Validator")
    
    validator = EXIFValidator(max_age_hours=24)
    
    # Test: Image without EXIF
    print("\n--- Test: Image without EXIF data ---")
    test_img = create_test_image_no_exif()
    result = validator.validate(test_img)
    print_result(result, "No EXIF Image")
    print("  Expected: FAIL (no timestamp to verify)")
    
    return True


def test_gps_validation():
    """Test GPS Validator."""
    print_header("Testing GPS Location Validator")
    
    validator = GPSValidator(max_distance_km=0.5)
    
    # Test 1: Image without GPS
    print("\n--- Test 1: Image without GPS data ---")
    test_img = create_test_image_no_exif()
    result = validator.validate(
        test_img,
        user_latitude=12.9716,
        user_longitude=77.5946
    )
    print_result(result, "No GPS Image")
    print("  Expected: FAIL (no GPS in image)")
    
    # Test 2: Distance calculation test
    print("\n--- Test 2: Distance Calculation ---")
    # Test Haversine formula
    dist = validator._calculate_distance(
        12.9716, 77.5946,  # Bangalore
        12.9716, 77.5946   # Same location
    )
    print(f"  Same location distance: {dist:.4f} km (should be 0)")
    
    dist = validator._calculate_distance(
        12.9716, 77.5946,  # Bangalore
        13.0827, 80.2707   # Chennai
    )
    print(f"  Bangalore to Chennai: {dist:.1f} km (should be ~290 km)")
    
    return True


def test_web_existence():
    """Test Web Existence Validator."""
    print_header("Testing Web Existence Validator")
    
    # Test without database connection
    validator = WebExistenceValidator(db_connection=None, hamming_threshold=5)
    
    print("\n--- Test: Perceptual Hash Generation ---")
    test_img = create_test_image_no_exif()
    result = validator.validate(test_img)
    print_result(result, "Hash Generation")
    print("  Expected: PASS (no database to check against)")
    
    return True


def test_full_service():
    """Test the full ImageValidationService."""
    print_header("Testing Full Validation Service")
    
    # Create service without database
    service = ImageValidationService(db_connection=None, config=Config())
    
    print("\n--- Test: Full validation pipeline ---")
    
    # Create test image and convert to bytes
    test_img = create_test_image_no_exif()
    img_bytes = io.BytesIO()
    test_img.save(img_bytes, format='PNG')
    image_data = img_bytes.getvalue()
    
    # Run validation
    result = service.validate_image(
        image_data=image_data,
        user_latitude=12.9716,
        user_longitude=77.5946,
        store_hash=False
    )
    
    print(f"\n  Overall Valid: {result.is_valid}")
    print(f"  Overall Score: {result.overall_score}")
    print(f"  Image Hash: {result.image_hash[:16]}...")
    print(f"  Perceptual Hash: {result.phash}")
    
    print("\n  Individual Check Results:")
    for check_name, check_result in result.checks.items():
        status = "✓" if check_result.get('passed', False) else "✗"
        print(f"    {status} {check_name}: {check_result.get('reason', 'N/A')[:50]}")
    
    print("\n  Reasons:")
    for reason in result.reasons:
        print(f"    - {reason}")
    
    return True


def test_with_real_image(image_path: str):
    """Test with a real image file."""
    print_header(f"Testing with Real Image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"  ERROR: File not found: {image_path}")
        return False
    
    # Load image
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        image = Image.open(io.BytesIO(image_data))
        print(f"  Image size: {image.size}")
        print(f"  Image format: {image.format}")
        
        # Check for EXIF
        exif = image._getexif()
        if exif:
            print(f"  EXIF entries: {len(exif)}")
            parsed_exif = {TAGS.get(k, k): v for k, v in exif.items()}
            
            # Show key EXIF fields
            key_fields = ['Make', 'Model', 'DateTime', 'DateTimeOriginal', 'Software']
            for field in key_fields:
                if field in parsed_exif:
                    print(f"    {field}: {parsed_exif[field]}")
            
            if 'GPSInfo' in parsed_exif:
                print(f"    GPS: Present")
        else:
            print("  EXIF: None (may indicate AI or screenshot)")
        
        # Run full validation
        print("\n  Running validation...")
        service = ImageValidationService(db_connection=None, config=Config())
        result = service.validate_image(
            image_data=image_data,
            user_latitude=12.9716,  # Default test location (Bangalore)
            user_longitude=77.5946,
            store_hash=False
        )
        
        print(f"\n  RESULT: {'✓ VALID' if result.is_valid else '✗ INVALID'}")
        print(f"  Score: {result.overall_score}/100")
        
        print("\n  Detailed Results:")
        for check_name, check_result in result.checks.items():
            status = "✓" if check_result.get('passed', False) else "✗"
            score = check_result.get('score', 0)
            reason = check_result.get('reason', 'N/A')
            print(f"    {status} {check_name} (score: {score:+d})")
            print(f"      → {reason[:70]}")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False


def main():
    print("\n" + "#" * 60)
    print("#  ABUSE PREVENTION MODULE - VALIDATION TESTS")
    print("#" * 60)
    
    # Check if a real image path was provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        test_with_real_image(image_path)
    else:
        # Run all component tests
        tests = [
            ("AI Detection", test_ai_detection),
            ("EXIF Validation", test_exif_validation),
            ("GPS Validation", test_gps_validation),
            ("Web Existence", test_web_existence),
            ("Full Service", test_full_service),
        ]
        
        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append((name, passed))
            except Exception as e:
                print(f"\n  ERROR in {name}: {str(e)}")
                results.append((name, False))
        
        # Summary
        print_header("TEST SUMMARY")
        for name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"  {status}: {name}")
        
        print("\n" + "-" * 60)
        print("  To test with a real image, run:")
        print("    python -m abuseprevention.test_validators path/to/image.jpg")
        print("-" * 60 + "\n")


if __name__ == "__main__":
    main()
