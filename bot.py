import os
import io
import re
import requests
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from urllib.parse import quote

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
    # word = "shenanigans" # DEBUG
    print(f"WOTD from RSS: {word}")

    # Step 2: Look up synonyms via the Collegiate Thesaurus API
    api_url = f"https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{quote(word)}?key={MW_TH_API_KEY}"

    api_response = requests.get(api_url)
    api_response.raise_for_status()
    data = api_response.json()
    #print(data) # DEBUG

    synonyms = []
    for entry in data:
        if isinstance(entry, dict) and "meta" in entry:
            syn_groups = entry["meta"].get("syns", [])
            if syn_groups:
                for syn in syn_groups[0]:  # only first sense group
                    if syn.lower() != word.lower() and syn.lower() not in synonyms:
                        synonyms.append(re.sub(r'[()]', '', syn).lower().strip())
            break  # only use first dictionary entry corresponding to definition 1

    return word, synonyms


def get_etymology(word):
    """Fetch etymology from the MW Collegiate Dictionary API."""
    api_url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{quote(word)}?key={MW_DI_API_KEY}"
    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()

    if not data or not isinstance(data[0], dict):
        return None

    et = data[0].get('et', None)
    if not et:
        return None

    # Extract only the main text block, ignore et_snote
    text = ""
    for item in et:
        if item[0] == 'text':
            text = item[1]
            break

    if not text:
        return None

    # Convert MW markup to Discord-compatible format
    # print(repr(text)) # DEBUG
    text = re.sub(r'\{it\}(.*?)\{/it\}', r'*\1*', text)              # italics to Discord format
    text = re.sub(r'\{ma\}\{mat\|(.*?)\|.*?\}\{/ma\}', '', text)     # remove "more at" cross-ref words
    text = re.sub(r'\{et_link\|.*?\}', '', text)                     # strip internal links
    text = re.sub(r'\s*\+\s*-\w+[\w\s-]*$', '', text)                # strip trailing fragments like "+ -sis theo-"
    text = re.sub(r'\{[^}]+\}', '', text)                            # strip any remaining tags
    text = text.strip()
    # print(repr(text)) # DEBUG

    return f'📖 **Etymology of "{word}":** {text}'


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


def get_rarity_label(frequency):
    """Return a rarity label based on ngram frequency thresholds."""
    # These thresholds are empirically derived. See the calibrate script and results
    if frequency >= 1e-4:
        return "very common"
    elif frequency >= 1e-5:
        return "common"
    elif frequency >= 1e-6:
        return "moderately common"
    elif frequency >= 1e-7:
        return "uncommon"
    elif frequency >= 1e-8:
        return "rare"
    else:
        return "very rare"


def generate_chart(ngram_data, words):
    """Generate a frequency chart image and return it as bytes."""
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))

    for entry in ngram_data:
        if entry["ngram"].lower() in [w.lower() for w in words]:
            years = list(range(NGRAMS_START_YEAR, NGRAMS_END_YEAR + 1))
            ax.plot(years, entry["timeseries"], label=entry["ngram"])

    ax.set_title("Word Frequency Over Time (Google Ngrams)", fontsize='20')
    ax.set_xlabel("Year", fontsize="x-large")
    ax.set_ylabel("Frequency (%)", fontsize="x-large")
    ax.legend(fontsize='x-large')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.4f}%'))
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close()
    return buf


def get_wiktionary_labels(word):
    """Fetch regional/usage labels from Wiktionary for a word."""
    headers = {'User-Agent': 'WOTDCommonalityBot/1.0 (educational Discord bot; contact via GitHub)'}
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={quote(word)}&prop=wikitext&format=json"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    if 'parse' not in data:
        return None
    
    wikitext = data['parse']['wikitext']['*']
    
    # Find all {{lb|en|...}} labels in the English section only
    # First, extract just the English section
    english_match = re.search(r'==English==\n(.*?)(?:\n==(?!=)|\Z)', wikitext, re.DOTALL)
    if not english_match:
        return None
    english_section = english_match.group(1)

    # Extract all lb|en templates (will contain regional keywords)
    lb_matches = re.findall(r'\{\{lb\|en\|(.*?)\}\}', english_section)

    # Regional labels we care about
    # NOTE: Could also parse for "slang" and "obsolete" in this same way, but not desired at the moment
    regional_keywords = {
        'Australia', 'Australian', 'New Zealand', 'British', 
        'UK', 'US', 'American', 'Canada', 'Canadian', 
        'Ireland', 'Irish', 'Scotland', 'Scottish'
    }
    
    found_regions = []
    for match in lb_matches:
        parts = match.split('|')
        for part in parts:
            part = part.strip()
            if part in regional_keywords and part not in found_regions:
                found_regions.append(part)
    
    return found_regions if found_regions else None


def build_insight(word, synonyms, ngram_data):
    """Build the insight text comparing the WOTD to its common synonyms."""
    if not ngram_data:
        return "Not enough data to calculate commonality."

    # Find the 3 most common synonyms
    display_synonyms = sorted(synonyms, key=lambda s: get_recent_frequency(ngram_data, s), reverse=True)[:3]
    print(f"Display Synonyms: {display_synonyms}") # DEBUG
    
    # Find the most common synonym among display_synonyms for the insight text
    best_syn = max(display_synonyms, key=lambda s: get_recent_frequency(ngram_data, s))
    best_syn_freq = get_recent_frequency(ngram_data, best_syn)

    wotd_freq = get_recent_frequency(ngram_data, word)
    if wotd_freq == 0 or best_syn_freq == 0:
        return display_synonyms, "Not enough data to calculate commonality."

    rarity = get_rarity_label(wotd_freq)

    if wotd_freq >= best_syn_freq:
        ratio = wotd_freq / best_syn_freq
        if ratio < 1.5:
            return(display_synonyms,f'"{word}" is {rarity} and about as common as "{best_syn}" in literature.')
        return(display_synonyms,f'"{word}" is {rarity} and {ratio:.1f}x more common than "{best_syn}" in literature.')
    else:
        ratio = best_syn_freq / wotd_freq
        if ratio < 1.5:
            return(display_synonyms,f'"{word}" is {rarity} and about as common as "{best_syn}" in literature.')
        return(display_synonyms,f'"{word}" is {rarity} and {ratio:.1f}x less common than "{best_syn}" in literature.')


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
    no_post_mode = False  # DEBUG: set to True to run without posting to Discord
    if not no_post_mode: post_to_discord('https://www.merriam-webster.com/word-of-the-day', None)
    word, synonyms = get_wotd()
    print(f"Word: {word}, Synonyms: {synonyms}")

    if not synonyms:
        print("No synonyms found, cannot compare.")
        ngram_data = get_ngrams_data([word])
        if ngram_data:
            chart_buf = generate_chart(ngram_data, [word])
            wotd_freq = get_recent_frequency(ngram_data, word)
            rarity = get_rarity_label(wotd_freq)
            if not no_post_mode: post_to_discord(f'"{word}" is {rarity}. No thesaurus entry found — showing frequency over time only.', chart_buf)
        else:
            if not no_post_mode: post_to_discord(f'No thesaurus entry found for "{word}" — commonality data unavailable for today\'s word.', None)
        print("Posted to Discord successfully.")
        return

    words = [word] + synonyms
    print(f"Fetching Ngrams data for: {words}")
    ngram_data = get_ngrams_data(words)

    if not ngram_data:
        print(f'No Ngrams data found for "{words}", cannot compare.')
        if not no_post_mode: post_to_discord(f'Not enough data to calculate commonality for "{word}".', None)
        print("Posted to Discord successfully.")
        return

    display_synonyms, insight = build_insight(word, synonyms, ngram_data)
    regions = get_wiktionary_labels(word)
    if regions:
        region_str = ", ".join(regions)
        insight += f"\n🌏 Regional note: primarily used in {region_str}"
    print(f"Insight: {insight}")

    chart_buf = generate_chart(ngram_data, [word] + display_synonyms)
    if not no_post_mode: post_to_discord(insight, chart_buf)

    etymology = get_etymology(word)
    if etymology:
        if not no_post_mode: post_to_discord(etymology, None)
        print(f"Etymology: {etymology}")
    else:
        if not no_post_mode: post_to_discord(f'📖 No etymology data found for "{word}".', None)
        print(f'No etymology data found for "{word}".')

    print("Posted to Discord successfully.")


if __name__ == "__main__":
    main()
