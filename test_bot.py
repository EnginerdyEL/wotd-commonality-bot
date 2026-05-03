#!/usr/bin/env python3
"""
Unit tests for bot.py - tests edge cases without posting to Discord
Run with: python3 test_bot.py
"""

import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the functions we need to test
# We'll need to modify bot.py slightly to export these functions
from bot import get_mw_dictionary_data

# Test cases: (word, description)
TEST_CASES = [
    ("boondoggle", "1. Happy path - common word with full data"),
    ("métier", "2. Accented characters - previously failed"),
    ("beltane", "3. Missing example sentence - should handle gracefully"),
    ("mea culpa", "4. Multi-word phrase - may have parsing challenges"),
    ("recondite", "5. Multiple pronunciations/audios - should handle all"),
]

def test_word(word):
    """Test a single word and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {word}")
    print(f"{'='*60}")
    
    try:
        pos, definition, example_sentence, etymology, audio_urls, prn = get_mw_dictionary_data(word)
        
        # Report results
        print(f"✓ Unpacking successful (6 values returned)")
        print(f"  - POS: {pos if pos else '(None)'}")
        print(f"  - Definition: {definition if definition else '(None)'}")
        print(f"  - Example: {example_sentence if example_sentence else '(None)'}")
        print(f"  - Etymology: {etymology if etymology else '(None)'}")
        print(f"  - Audio URLs: {len(audio_urls) if audio_urls else 0} file(s)")
        if audio_urls:
            for i, url in enumerate(audio_urls, 1):
                print(f"    {i}. {url}")
        print(f"  - Pronunciations: {len(prn) if prn else 0} variant(s)")
        if prn:
            for i, p in enumerate(prn, 1):
                print(f"    {i}. {p}")
        
        # Check for minimum viable data
        if pos is None:
            print(f"⚠ WARNING: No POS found")
        if definition is None:
            print(f"⚠ WARNING: No definition found")
        
        return True
        
    except ValueError as e:
        print(f"✗ FAILED: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED with unexpected error: {type(e).__name__}: {e}")
        return False

def main():
    """Run all test cases."""
    print("\n" + "="*60)
    print("WOTD Bot Unit Tests")
    print("="*60)
    
    results = []
    for word, description in TEST_CASES:
        print(f"\n{description}")
        success = test_word(word)
        results.append((word, success))
    
    # Summary
    print(f"\n\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for word, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {word}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! No regressions detected.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Review above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())