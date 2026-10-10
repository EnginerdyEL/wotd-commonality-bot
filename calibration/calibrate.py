import csv
import os
import requests
import sys
sys.path.append('..')
from dotenv import load_dotenv
from tools import Tools
from wik_dict_tools import Wik_Dict_Tools
from word_tools import Word_Tools

# Load secrets from .env for local testing
load_dotenv()

DEBUG = True

MW_DI_API_KEY = os.environ["MW_DI_API_KEY"]
MW_TH_API_KEY = os.environ["MW_TH_API_KEY"]

def get_all_frequencies(words):
    """Get all frequencies of the words over a calibration time period"""
    word_tools = Word_Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)
    tools = Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)

    ngram_data = word_tools.get_ngrams_data(words)
    if not ngram_data:
        print(f"[{tools.ts()}] No Ngrams data found current set.")
        return
    frequency_set = []
    """Get the average frequency of a word over the last 30 years of data."""
    """Note that word_tools.py get_recent_frequency does nearly the same function"""
    for entry in ngram_data:
        frequencies_recent = entry["timeseries"][-30:]
        frequency_set.append(sum(frequencies_recent) / len(frequencies_recent))
    return frequency_set


def main():
    SPOT_CHECK_MODE = True  # Set to False to run full calibration, writing to results.csv
    SPOT_CHECK_WORDS = ['gregarious', 'inscrutable', 'perspicacious']

    word_tools = Word_Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)
    tools = Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)
    wik_dict_tools = Wik_Dict_Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)

    if SPOT_CHECK_MODE:
        print(f"[{tools.ts()}] Spot check mode:")
        freq_set = get_all_frequencies(SPOT_CHECK_WORDS)
        for word, freq in zip(SPOT_CHECK_WORDS, freq_set):
            rarity = word_tools.get_rarity_label(freq)
            # _, regions = wik_dict_tools.get_wiktionary_data(word)
            # region_str = f"[{', '.join(regions)}]" if regions else ""
            region_str = "" # DEBUG
            print(f"[{tools.ts()}] {word}: {freq:.2e} ({rarity}) {region_str}")
        return

    words_very_common = ['the', 'happy', 'house', 'walk', 'money', 'love', 'time', 'good', 'work', 'day']
    words_common = ['eloquent', 'vibrant', 'serene', 'curious', 'stubborn', 'graceful', 'wander', 'ponder', 'vivid', 'fragile']
    words_uncommon = ['ephemeral', 'luminous', 'melancholy', 'tenacious', 'ubiquitous', 'verbose', 'candid', 'whimsical', 'stoic', 'resilient']
    words_rare = ['tranche', 'mea culpa', 'callipygian', 'sycophant', 'perspicacious', 'mellifluous', 'defenestrate', 'soliloquy', 'loquacious', 'pusillanimous']

    all_groups = [
        ('very_common', words_very_common),
        ('common', words_common),
        ('uncommon', words_uncommon),
        ('rare', words_rare),
    ]

    rows = []
    for group_name, words in all_groups:
        print(f"[{tools.ts()}] Fetching ngrams data for: {group_name}")
        frequency_set = get_all_frequencies(words)
        if not frequency_set:
            continue
        for word, freq in zip(words, frequency_set):
            rows.append({'word': word, 'group': group_name, 'frequency': freq})

    # Write to CSV
    with open('results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['word', 'group', 'frequency'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[{tools.ts()}] Results written to results.csv ({len(rows)} words)")

    # Print summary per group
    for group_name, words in all_groups:
        group_rows = [r for r in rows if r['group'] == group_name]
        if group_rows:
            freqs = [r['frequency'] for r in group_rows]
            print(f"[{tools.ts()}] {group_name}: min={min(freqs):.2e}, max={max(freqs):.2e}")


if __name__ == "__main__":
    main()
