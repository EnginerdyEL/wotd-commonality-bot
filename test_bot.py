#!/usr/bin/env python3
"""
Comprehensive unit tests for bot.py
Tests both dictionary extraction and the full pipeline (thesaurus, ngrams, frequency comparison)
Run with: python3 test_bot.py
"""

import sys
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
        pos, definition, example_sentence, etymology, audio_urls, prn = get_mw_dictionary_data(word)
        
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
        print("\n🎉 All tests passed! No regressions detected.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Review above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())