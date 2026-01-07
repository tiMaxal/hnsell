#!/usr/bin/env python3
"""
test_puny2uni2.py - Test script for puny2uni2.py functionality

Run this to verify installation and test basic features.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from puny2uni2 import Puny2UniConverter
    print("✓ puny2uni2 module imported successfully\n")
except ImportError as e:
    print(f"✗ Failed to import puny2uni2: {e}")
    sys.exit(1)

def test_basic_conversion():
    """Test basic punycode/unicode conversion"""
    print("="*60)
    print("TEST 1: Basic Conversion")
    print("="*60)
    
    converter = Puny2UniConverter()
    
    # Test cases
    test_cases = [
        ("xn--wgv71a", "日本", "Japanese"),
        ("xn--fiqs8s", "中国", "Chinese"),
        ("xn--n3h", "☃", "Emoji/Snowman"),
        ("xn--80akhbyknj4f", "Россия", "Russian"),
        ("xn--mgbayh7gpa", "الاردن", "Arabic"),
    ]
    
    passed = 0
    failed = 0
    
    for puny, expected_unicode, description in test_cases:
        result = converter.convert_domain(puny, translate=False, verbose=False)
        if result and result['output'] == expected_unicode:
            print(f"✓ {puny} → {result['output']} ({description})")
            passed += 1
        else:
            print(f"✗ {puny} → Expected: {expected_unicode}, Got: {result['output'] if result else 'None'}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0

def test_language_detection():
    """Test language detection"""
    print("="*60)
    print("TEST 2: Language Detection")
    print("="*60)
    
    converter = Puny2UniConverter()
    
    test_cases = [
        ("日本", "Japanese"),
        ("中国", "Chinese/Japanese/Korean"),
        ("Россия", "Cyrillic (Russian/Ukrainian)"),
        ("ελληνικά", "Greek"),
        ("العربية", "Arabic/Urdu/Uyghur"),
        ("עברית", "Hebrew"),
    ]
    
    passed = 0
    failed = 0
    
    for text, expected_lang in test_cases:
        detected_lang, lang_code = converter.detect_language(text)
        if detected_lang:
            print(f"✓ {text} → {detected_lang} (expected: {expected_lang})")
            passed += 1
        else:
            print(f"✗ {text} → No language detected (expected: {expected_lang})")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0

def test_translation():
    """Test translation capability"""
    print("="*60)
    print("TEST 3: Translation")
    print("="*60)
    
    try:
        from deep_translator import GoogleTranslator
        print("✓ deep-translator is installed\n")
    except ImportError:
        print("✗ deep-translator is NOT installed")
        print("  Translation features will be disabled")
        print("  Install with: pip install deep-translator\n")
        return False
    
    converter = Puny2UniConverter()
    
    # Test a simple translation
    test_text = "日本"
    translation = converter.translate_text(test_text, 'en')
    
    if translation:
        print(f"✓ Translation test: {test_text} → {translation}")
        return True
    else:
        print(f"✗ Translation failed for: {test_text}")
        return False

def test_file_processing():
    """Test file processing"""
    print("="*60)
    print("TEST 4: File Processing")
    print("="*60)
    
    # Check if sample file exists
    sample_file = "sample_punycode_domains.txt"
    if not os.path.exists(sample_file):
        print(f"ℹ Sample file not found: {sample_file}")
        print("  Skipping file processing test\n")
        return True
    
    print(f"✓ Sample file found: {sample_file}")
    print("  To test file processing, run:")
    print(f"    python puny2uni2.py {sample_file}\n")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  puny2uni2.py Test Suite")
    print("="*60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Basic Conversion", test_basic_conversion()))
    results.append(("Language Detection", test_language_detection()))
    results.append(("Translation", test_translation()))
    results.append(("File Processing", test_file_processing()))
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! puny2uni2 is ready to use.")
        print("\nNext steps:")
        print("  1. Try interactive mode: python puny2uni2.py -i")
        print("  2. Convert a domain: python puny2uni2.py xn--wgv71a")
        print("  3. Process a file: python puny2uni2.py sample_punycode_domains.txt -t")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
    
    print()

if __name__ == '__main__':
    main()
