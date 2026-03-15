import os
import io
import requests
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load secrets from .env for local testing
load_dotenv()

MW_DI_API_KEY = os.environ["MW_DI_API_KEY"]
MW_TH_API_KEY = os.environ["MW_TH_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

NGRAMS_START_YEAR = 1900
NGRAMS_END_YEAR = 2019


def get_wotd():
    """Fetch the Word of the Day from MW RSS feed, then look up synonyms via the API."""
    # Step 1: Get the word from the RSS feed
    rss_url = "https://www.merriam-webster.com/wotd/feed/rss2"
    response = requests.get(rss_url)
    response.raise_for_status()

    # Parse the word from the RSS XML
    root = ET.fromstring(response.content)
    # The first item in the feed is today's word
    first_item = root.find(".//item")
    word = first_item.find("title").text.strip().lower()
    #word = "happy" # DEBUG
    print(f"WOTD from RSS: {word}")

    # Step 2: Look up synonyms via the Collegiate Thesaurus API
    api_url = f"https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key={MW_TH_API_KEY}"

    api_response = requests.get(api_url)
    api_response.raise_for_status()
    data = api_response.json()
    #print(data) # DEBUG

    synonyms = []
    for entry in data:
        if isinstance(entry, dict) and "meta" in entry:
            for syn_list in entry["meta"].get("syns", []):
                for syn in syn_list:
                    if syn.lower() != word.lower() and syn.lower() not in synonyms:
                        synonyms.append(syn.lower())
        if len(synonyms) >= 3:
            break

    return word, synonyms[:3]


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


def get_recent_frequency(ngram_data, word):
    """Get the average frequency of a word over the last 10 years of data."""
    for entry in ngram_data:
        if entry["ngram"].lower() == word.lower():
            recent = entry["timeseries"][-10:]
            return sum(recent) / len(recent) if recent else 0
    return 0


def generate_chart(ngram_data, words):
    """Generate a frequency chart image and return it as bytes."""
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))

    for entry in ngram_data:
        if entry["ngram"].lower() in [w.lower() for w in words]:
            years = list(range(NGRAMS_START_YEAR, NGRAMS_END_YEAR + 1))
            ax.plot(years, entry["timeseries"], label=entry["ngram"])

    ax.set_title("Word Frequency Over Time (Google Ngrams)", fontsize=14)
    ax.set_xlabel("Year")
    ax.set_ylabel("Frequency (%)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close()
    return buf


def build_insight(word, synonyms, ngram_data):
    """Build the insight text comparing the WOTD to its closest synonym."""
    if not ngram_data:
        return "Not enough data to calculate commonality."

    wotd_freq = get_recent_frequency(ngram_data, word)

    # Find the most frequent synonym with data
    best_syn = None
    best_syn_freq = 0
    for syn in synonyms:
        freq = get_recent_frequency(ngram_data, syn)
        if freq > best_syn_freq:
            best_syn_freq = freq
            best_syn = syn

    if best_syn is None or wotd_freq == 0 and best_syn_freq == 0:
        return "Not enough data to calculate commonality."

    # Avoid division by zero
    if wotd_freq == 0 or best_syn_freq == 0:
        return "Not enough data to calculate commonality."

    if wotd_freq >= best_syn_freq:
        ratio = wotd_freq / best_syn_freq
        if ratio < 1.5:
            return f'"{word}" and "{best_syn}" are about equally common in literature.'
        return f'"{word}" is {ratio:.1f}x more common than "{best_syn}" in literature.'
    else:
        ratio = best_syn_freq / wotd_freq
        if ratio < 1.5:
            return f'"{word}" and "{best_syn}" are about equally common in literature.'
        return f'"{best_syn}" is {ratio:.1f}x more common than "{word}" in literature.'


def post_to_discord(insight, chart_buf):
    """Post the insight text and chart image to Discord via webhook."""
    payload = {"content": insight, "username": "Wordy"}
    if chart_buf is not None:
        files = {"file": ("chart.png", chart_buf, "image/png")}
        response = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
    else:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    response.raise_for_status()


def main():
    print("Fetching Word of the Day and posting to Discord")
    post_to_discord('https://www.merriam-webster.com/word-of-the-day', None)
    word, synonyms = get_wotd()
    print(f"Word: {word}, Synonyms: {synonyms}")

    if not synonyms:
        print("No synonyms found, cannot compare.")
        ngram_data = get_ngrams_data([word])
        if ngram_data:
            chart_buf = generate_chart(ngram_data, [word])
            post_to_discord(f'No thesaurus entry found for "{word}" — showing frequency over time only.', chart_buf)
        else:
            post_to_discord(f'No thesaurus entry found for "{word}" — commonality data unavailable for today\'s word.', None)
        print("Posted to Discord successfully.")
        return

    words = [word] + synonyms
    print(f"Fetching Ngrams data for: {words}")
    ngram_data = get_ngrams_data(words)

    if not ngram_data:
        print(f'No Ngrams data found for "{words}", cannot compare.')
        post_to_discord(f'Not enough data to calculate commonality for "{word}".', None)
        print("Posted to Discord successfully.")
        return

    insight = build_insight(word, synonyms, ngram_data)
    print(f"Insight: {insight}")

    chart_buf = generate_chart(ngram_data, words)
    post_to_discord(insight, chart_buf)
    print("Posted to Discord successfully.")


if __name__ == "__main__":
    main()
