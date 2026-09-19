#!/usr/bin/env python3
"""
Comprehensive unit tests for bot.py
Tests both dictionary extraction and the full pipeline (thesaurus, ngrams, frequency comparison)
Run with: python3 test_bot.py
"""

import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the functions we need to test
from bot import (
    get_mw_dictionary_data,
    get_mw_thesaurus_data,
    get_ngrams_data,
    get_recent_frequency,
    get_rarity_label
)

# Test cases: (word, description, should_have_synonyms)
# should_have_synonyms indicates if we expect thesaurus data for integration testing
TEST_CASES = [
    ("boondoggle", "1. Happy path - common word with full data", True),
    ("métier", "2. Accented characters - previously failed", False),
    ("beltane", "3. Rare/specialized - missing example sentence", False),
    ("mea culpa", "4. Multi-word phrase - parsing challenges", False),
    ("recondite", "5. Multiple pronunciations/audios", True),
    ("speculate", "6. Common word with synonym data", True),
    ("adroit", "7. Adjective with rich thesaurus entry", True),
]


def test_dictionary_data(word):
    """Test dictionary data extraction."""
    print(f"\n  Dictionary Extraction:")
    try:
        pos, definition, example_sentence, etymology, audio_urls, prn, sense_idx, formality = get_mw_dictionary_data(word)
        
        print(f"    ✓ POS: {pos if pos else '(None)'}")
        print(f"    ✓ Definition: {definition[:50] + '...' if definition and len(definition) > 50 else definition if definition else '(None)'}")
        print(f"    ✓ Example: {example_sentence[:50] + '...' if example_sentence and len(example_sentence) > 50 else example_sentence if example_sentence else '(None)'}")
        print(f"    ✓ Etymology: {'Present' if etymology else '(None)'}")
        print(f"    ✓ Audio files: {len(audio_urls) if audio_urls else 0}")
        if audio_urls:
            for i, url in enumerate(audio_urls, 1):
                print(f"      {i}. {url}")
        print(f"    ✓ Pronunciations: {len(prn) if prn else 0} variant(s)")
        if prn:
            for i, p in enumerate(prn, 1):
                print(f"      {i}. {p}")
        
        # Check for minimum viable data
        has_warnings = False
        if pos is None:
            print(f"    ⚠ WARNING: No POS found")
            has_warnings = True
        if definition is None:
            print(f"    ⚠ WARNING: No definition found")
            has_warnings = True
        
        return True, not has_warnings
        
    except Exception as e:
        print(f"    ✗ FAILED: {type(e).__name__}: {e}")
        return False, False


def test_thesaurus_data(word):
    """Test thesaurus/synonym lookup."""
    print(f"\n  Thesaurus Lookup:")
    try:
        synonyms = get_mw_thesaurus_data(word)
        
        if synonyms:
            print(f"    ✓ Found {len(synonyms)} synonym(s): {', '.join(synonyms[:3])}")
            if len(synonyms) > 3:
                print(f"      (and {len(synonyms) - 3} more)")
            return True, synonyms
        else:
            print(f"    ℹ No synonyms found (expected for rare/specialized words)")
            return True, None
            
    except Exception as e:
        print(f"    ✗ FAILED: {type(e).__name__}: {e}")
        return False, None


def test_frequency_data(word, synonyms):
    """Test ngrams frequency lookup and comparison."""
    print(f"\n  Frequency Analysis:")
    try:
        # Look up the word itself
        words_to_lookup = [word]
        if synonyms:
            words_to_lookup.extend(synonyms[:3])  # Test with word + top 3 synonyms
        
        ngram_data = get_ngrams_data(words_to_lookup)
        print(f"    ✓ Fetched ngram data for {len(words_to_lookup)} word(s)")
        
        # Test frequency extraction
        word_freq = get_recent_frequency(ngram_data, word)
        print(f"    ✓ Recent frequency for '{word}': {word_freq:.2e}")
        
        # Test rarity labeling
        rarity = get_rarity_label(word_freq)
        print(f"    ✓ Rarity label: {rarity}")
        
        # Test comparisons with synonyms
        if synonyms:
            print(f"    ✓ Frequency comparisons:")
            for syn in synonyms[:2]:  # Show first 2 synonyms
                syn_freq = get_recent_frequency(ngram_data, syn)
                if word_freq > 0:
                    ratio = syn_freq / word_freq
                    print(f"      - '{syn}' is {ratio:.1f}x the frequency of '{word}'")
                else:
                    print(f"      - '{syn}' frequency: {syn_freq:.2e}")
        
        return True
        
    except Exception as e:
        print(f"    ✗ FAILED: {type(e).__name__}: {e}")
        return False


def test_word(word, should_have_synonyms):
    """Test a single word through dictionary extraction and optionally the full pipeline."""
    print(f"\n{'='*70}")
    print(f"Testing: {word}")
    print(f"{'='*70}")
    
    results = {
        'dictionary': False,
        'thesaurus': False,
        'frequency': False,
    }
    
    # Test 1: Dictionary extraction (always run)
    dict_ok, dict_quality = test_dictionary_data(word)
    results['dictionary'] = dict_ok
    
    # Test 2: Thesaurus lookup (always run)
    thesaurus_ok, synonyms = test_thesaurus_data(word)
    results['thesaurus'] = thesaurus_ok
    
    # Check expectations vs reality
    if should_have_synonyms and not synonyms:
        print(f"  ⚠ WARNING: Expected synonyms but found none")
    elif not should_have_synonyms and synonyms:
        print(f"  ℹ Found synonyms despite expecting none (bonus!)")
    
    # Test 3: Frequency analysis (only if we have data)
    if results['dictionary'] and results['thesaurus'] and synonyms:
        results['frequency'] = test_frequency_data(word, synonyms)
    else:
        if not synonyms:
            print(f"\n  Frequency Analysis: Skipped (no synonyms for comparison)")
        else:
            print(f"\n  Frequency Analysis: Skipped (missing prerequisite data)")
        results['frequency'] = True  # Don't count as failure
    
    # Overall result
    all_pass = all(results.values())
    return all_pass, results


def test_etymology(etymology_cases_file="etymology_test_cases.json"):
    """Test etymology extraction against known expected values."""
    print(f"\n\n{'='*70}")
    print("ETYMOLOGY EXTRACTION TESTS (TDD - Expected Failures)")
    print(f"{'='*70}\n")
    
    try:
        with open(etymology_cases_file, 'r') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {etymology_cases_file} not found in current directory")
        return False
    
    test_cases = test_data['test_cases']
    results = []
    
    for test_case in test_cases:
        word = test_case['word']
        expected = test_case['expected']
        notes = test_case['notes']
        
        print(f"\nWord: {word}")
        print(f"Notes: {notes}")
        
        try:
            # Run the bot on this word
            _, _, _, etymology, _, _, _, _ = get_mw_dictionary_data(word)
            
            if etymology is None:
                actual_raw = "(None)"
                actual = "(None)"
                passed = False
            else:
                actual_raw = etymology
                # Strip the "📖 **Etymology of *word*:** " prefix for comparison
                # The actual format has bold markers: :** not just :
                if ":** " in etymology:
                    actual = etymology.split(":** ", 1)[1]
                elif ": " in etymology:
                    actual = etymology.split(": ", 1)[1]
                else:
                    actual = etymology
                
                # Remove asterisks (italics/bold markers) for cleaner comparison
                actual_normalized = actual.replace("*", "")
                expected_normalized = expected.replace("*", "")
                
                passed = actual_normalized.strip() == expected_normalized.strip()
            
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}")
            
            if not passed:
                print(f"\nExpected:")
                print(f"  {expected}")
                print(f"\nActual (raw from bot):")
                print(f"  {actual_raw}")
                print(f"\nActual (repr - exact bytes):")
                print(f"  {repr(actual_raw)}")
                print(f"\nAfter stripping prefix:")
                print(f"  {actual}")
                print(f"  (repr: {repr(actual)})")
                print(f"\nAfter removing asterisks:")
                print(f"  Expected: '{expected_normalized}'")
                print(f"  Actual:   '{actual_normalized}'")
                print()
            
            results.append((word, passed))
            
        except Exception as e:
            print(f"✗ EXCEPTION: {type(e).__name__}: {e}")
            results.append((word, False))
    
    # Summary
    print(f"\n{'='*70}")
    print("ETYMOLOGY TEST SUMMARY")
    print(f"{'='*70}\n")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for word, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {word}")
    
    print(f"\n{passed}/{total} etymology tests passed")
    
    if passed == total:
        print("\n🎉 All etymology tests passed!\n")
    else:
        print(f"\n❌ {total - passed} etymology test(s) failed. Review above for details.\n")
    
    return passed == total, results  # Return pass/fail and results for summary


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("WOTD Bot Comprehensive Unit Tests")
    print("="*70)
    print("\nTests dictionary extraction for all words")
    print("Tests full pipeline (thesaurus + ngrams) when applicable\n")
    
    results = []
    for word, description, should_have_synonyms in TEST_CASES:
        print(f"{description}")
        success, test_results = test_word(word, should_have_synonyms)
        results.append((word, success, test_results))
    
    # Summary
    print(f"\n\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for word, success, test_results in results:
        status = "✓ PASS" if success else "✗ FAIL"
        checks = ", ".join(
            f"{'✓' if test_results[k] else '✗'} {k.title()}"
            for k in ['dictionary', 'thesaurus', 'frequency']
        )
        print(f"{status}: {word:15} [{checks}]")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All word tests passed! No regressions detected.\n")
        return 0, results  # Return exit code and results for summary
    else:
        print(f"\n❌ {total - passed} word test(s) failed. Review above for details.\n")
        return 1, results  # Return exit code and results for summary


if __name__ == "__main__":
    # Run word tests first, then etymology tests
    word_exit_code, word_results = main()
    etymology_passed, etymology_results = test_etymology()
    
    # Unified summary at the end
    print(f"\n\n{'='*70}")
    print("UNIFIED TEST SUMMARY")
    print(f"{'='*70}\n")
    
    print("WORD EXTRACTION TESTS:")
    for word, all_pass, test_results in word_results:
        dict_ok = test_results.get('dictionary', False)
        thes_ok = test_results.get('thesaurus', False)
        freq_ok = test_results.get('frequency', False)
        status = "✓ PASS" if all_pass else "✗ FAIL"
        print(f"{status}: {word:20} [{'✓ Dictionary' if dict_ok else '✗ Dictionary'}, {'✓ Thesaurus' if thes_ok else '✗ Thesaurus'}, {'✓ Frequency' if freq_ok else '✗ Frequency'}]")
    
    word_passed = sum(1 for _, all_pass, _ in word_results if all_pass)
    print(f"\n{word_passed}/{len(word_results)} word tests passed")
    
    print(f"\n{'='*70}\n")
    print("ETYMOLOGY TESTS:")
    for word, success in etymology_results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {word}")
    
    etymology_passed_count = sum(1 for _, success in etymology_results if success)
    print(f"\n{etymology_passed_count}/{len(etymology_results)} etymology tests passed")
    
    print(f"\n{'='*70}\n")
    
    total_passed = word_passed + etymology_passed_count
    total_tests = len(word_results) + len(etymology_results)
    
    if total_passed == total_tests:
        print(f"🎉 ALL TESTS PASSED! ({total_passed}/{total_tests})\n")
        sys.exit(0)
    else:
        print(f"❌ {total_tests - total_passed} TEST(S) FAILED ({total_passed}/{total_tests})\n")
        sys.exit(1)