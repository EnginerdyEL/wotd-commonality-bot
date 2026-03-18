import csv
import requests

NGRAMS_START_YEAR = 2010
NGRAMS_END_YEAR = 2019


def get_ngrams_data(words):
    """Fetch frequency data from Google Ngrams for a list of words."""
    content = ",".join(words)
    url = (
        f"https://books.google.com/ngrams/json"
        f"?content={content}"
        f"&year_start={NGRAMS_START_YEAR}"
        f"&year_end={NGRAMS_END_YEAR}"
        f"&corpus=en-2019"
        f"&smoothing=3"
    )
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_all_frequencies(words):
    """Get all frequencies of the words over a calibration time period"""
    ngram_data = get_ngrams_data(words)
    if not ngram_data:
        print('No Ngrams data found current set.')
        return
    frequency_set = []
    for entry in ngram_data:
        frequencies_recent = entry["timeseries"][:]
        frequency_set.append(sum(frequencies_recent) / len(frequencies_recent))
    return frequency_set


def main():
    SPOT_CHECK_MODE = False  # Set to False to run full calibration
    SPOT_CHECK_WORDS = ['putative', 'verbose']

    if SPOT_CHECK_MODE:
        print("Spot check mode:")
        freq_set = get_all_frequencies(SPOT_CHECK_WORDS)
        for word, freq in zip(SPOT_CHECK_WORDS, freq_set):
            print(f"{word}: {freq:.2e}")
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
        print(f"Fetching ngrams data for: {group_name}")
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

    print(f"\nResults written to results.csv ({len(rows)} words)")

    # Print summary per group
    for group_name, words in all_groups:
        group_rows = [r for r in rows if r['group'] == group_name]
        if group_rows:
            freqs = [r['frequency'] for r in group_rows]
            print(f"{group_name}: min={min(freqs):.2e}, max={max(freqs):.2e}")


if __name__ == "__main__":
    main()
