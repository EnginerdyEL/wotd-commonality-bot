import os
import io
import re
import requests
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote

# Load secrets from .env for local testing
load_dotenv()

MW_DI_API_KEY = os.environ["MW_DI_API_KEY"]
MW_TH_API_KEY = os.environ["MW_TH_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

NGRAMS_START_YEAR = 1900
NGRAMS_END_YEAR = 2019


def ts():
    """Return current timestamp string for logging."""
    return (f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}")[:-5]


def get_wotd():
    """Fetch the Word of the Day from MW RSS feed, then look up synonyms via the API."""
    # Step 1: Get the word from the RSS feed
    rss_url = "https://www.merriam-webster.com/wotd/feed/rss2"
    response = requests.get(rss_url)
    response.raise_for_status()

    # Parse the word from the RSS XML. The first item in the feed is today's word
    root = ET.fromstring(response.content)
    first_item = root.find(".//item")
    word = first_item.find("title").text.strip().lower()
    # word = "almond" # DEBUG
    print(f"[{ts()}] WOTD from RSS: {word}")

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


def get_mw_dictionary_data(word):
    """Fetch etymology and audio pronunciation URL from the MW Collegiate Dictionary API."""
    api_url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{quote(word)}?key={MW_DI_API_KEY}"
    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()

    if not data or not isinstance(data[0], dict):
        return None, None

    entry = data[0]

    # Extract etymology
    etymology = None
    et = entry.get('et', None)
    if et:
        text = ""
        for item in et:
            if item[0] == 'text':
                text = item[1]
                break
        if text:
            text = re.sub(r'\{it\}(.*?)\{/it\}', r'*\1*', text)
            text = re.sub(r'\{ma\}\{mat\|(.*?)\|.*?\}\{/ma\}', '', text)
            text = re.sub(r'\{et_link\|.*?\}', '', text)
            text = re.sub(r'\s*\+\s*-\w+[\w\s-]*$', '', text)
            text = re.sub(r'\{[^}]+\}', '', text)
            text = text.strip()
            etymology = f'📖 **Etymology of "{word}":** {text}'

    # Extract audio URLs (may have multiple pronunciations)
    audio_urls = []
    prs = entry.get('hwi', {}).get('prs', [])
    for pr in prs:
        if 'sound' in pr:
            audio_file = pr['sound']['audio']
            if audio_file.startswith('bix'):
                subdir = 'bix'
            elif audio_file.startswith('gg'):
                subdir = 'gg'
            elif audio_file[0].isdigit():
                subdir = 'number'
            else:
                subdir = audio_file[0]
            audio_urls.append(f"https://media.merriam-webster.com/audio/prons/en/us/mp3/{subdir}/{audio_file}.mp3")

    return etymology, audio_urls if audio_urls else None    # Extract audio URL


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


def get_wiktionary_data(word):
    """Fetch regional/usage labels and IPA pronunciation from Wiktionary."""
    headers = {'User-Agent': 'WOTDCommonalityBot/1.0 (educational Discord bot; contact via GitHub)'}
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={quote(word)}&prop=wikitext&format=json"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if 'parse' not in data:
        return None, None

    wikitext = data['parse']['wikitext']['*']

    # Extract English section only
    english_match = re.search(r'==English==\n(.*?)(?:\n==(?!=)|\Z)', wikitext, re.DOTALL)
    if not english_match:
        return None, None
    english_section = english_match.group(1)

    # Extract IPA
    ipa_match = re.search(r'\{\{IPA\|en\|(/[^/]+/)', english_section)
    ipa = ipa_match.group(1) if ipa_match else None

    # Extract regional labels
    regional_keywords = {
        'Australia', 'Australian', 'New Zealand', 'British',
        'UK', 'US', 'American', 'Canada', 'Canadian',
        'Ireland', 'Irish', 'Scotland', 'Scottish'
    }
    lb_matches = re.findall(r'\{\{lb\|en\|(.*?)\}\}', english_section)
    found_regions = []
    for match in lb_matches:
        parts = match.split('|')
        for part in parts:
            part = part.strip()
            if part in regional_keywords and part not in found_regions:
                found_regions.append(part)
    regions = found_regions if found_regions else None

    return ipa, regions


def build_insight(word, synonyms, ngram_data):
    """Build the insight text comparing the WOTD to its common synonyms."""
    if not ngram_data:
        return "Not enough data to calculate commonality."

    # Find the 3 most common synonyms
    display_synonyms = sorted(synonyms, key=lambda s: get_recent_frequency(ngram_data, s), reverse=True)[:3]
    print(f"[{ts()}] Display Synonyms: {display_synonyms}") # DEBUG
    
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
    print(f"[{ts()}] Fetching Word of the Day and posting to Discord")
    no_post_mode = False  # DEBUG: set to True to run without posting to Discord
    if not no_post_mode: post_to_discord('https://www.merriam-webster.com/word-of-the-day', None)
    word, synonyms = get_wotd()
    # print(f"[{ts()}] Word: {word}, Synonyms: {synonyms}") # DEBUG

    chart_buf = None
    if not synonyms:
        print(f"[{ts()}] No synonyms found, cannot compare.")
        ngram_data = get_ngrams_data([word])
        if ngram_data:
            chart_buf = generate_chart(ngram_data, [word])
            wotd_freq = get_recent_frequency(ngram_data, word)
            rarity = get_rarity_label(wotd_freq)
            commonality = '"' + word + '" is ' + rarity + '. No thesaurus entry found — showing frequency over time only.'
        else:
            commonality = 'No thesaurus entry found for' + word + ' — commonality data unavailable for today\'s word.'
    else:
        words = [word] + synonyms
        print(f"[{ts()}] Fetching Ngrams data for: {words}")
        ngram_data = get_ngrams_data(words)

        if not ngram_data:
            print(f"[{ts()}] No Ngrams data found for {words}, cannot compare.")
            if not no_post_mode: post_to_discord(f'Not enough data to calculate commonality for "{word}".', None)
            print(f"[{ts()}] Posted to Discord successfully.")
        else:
            display_synonyms, commonality = build_insight(word, synonyms, ngram_data)
            chart_buf = generate_chart(ngram_data, [word] + display_synonyms)

    ipa, regions = get_wiktionary_data(word)
    etymology, audio_urls = get_mw_dictionary_data(word)

    # Build insight in desired order: pronunciation, audio, commonality, regional note
    insight_parts = []
    if ipa:
        if audio_urls:
            if len(audio_urls) == 1:
                insight_parts.append(f"🔊 Pronunciation: {ipa}  🎵  [Audio Example]({audio_urls[0]})")
            else:
                audio_links = "  ".join([f"🎵  [Audio Example {i+1}]({url})" for i, url in enumerate(audio_urls)])
                insight_parts.append(f"🔊 Pronunciation: {ipa}{audio_links}")
        else:
            insight_parts.append(f"🔊 Pronunciation: {ipa}")

    insight_parts.append(commonality)

    if regions:
        insight_parts.append(f"🌏 Regional note: primarily used in {', '.join(regions)}")
    
    insight = "\n".join(insight_parts)
    print(f"[{ts()}] Insight: {insight}")

    if not no_post_mode: post_to_discord(insight, chart_buf)

    if etymology:
        if not no_post_mode: post_to_discord(etymology, None)
        print(f"[{ts()}] Etymology: {etymology}")
    else:
        if not no_post_mode: post_to_discord(f'📖 No etymology data found for "{word}".', None)
        print(f"[{ts()}] No etymology data found for {word}.")

    print(f"[{ts()}] Posted to Discord successfully.")


if __name__ == "__main__":
    main()
