import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from word_tools import Word_Tools
from mw_dict_tools import MW_Dict_Tools
from wik_dict_tools import Wik_Dict_Tools

# Load secrets from .env for local testing
load_dotenv()

# DEBUG Flag: Set to True to show debug output, False to hide
DEBUG = True

MW_DI_API_KEY = os.environ["MW_DI_API_KEY"]
MW_TH_API_KEY = os.environ["MW_TH_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def ts():
    """Return current timestamp string for logging."""
    return (f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}")[:-5]

def debug(message):
    """Print debug message only if DEBUG flag is True."""
    if DEBUG:
        print(f"[{ts()}] DEBUG: {message}")

def get_wotd(mw_dict_tools):
    """Fetch the Word of the Day from MW RSS feed, then look up synonyms via the API."""
    # Step 1: Get the word from the RSS feed
    rss_url = "https://www.merriam-webster.com/wotd/feed/rss2"
    response = requests.get(rss_url)
    response.raise_for_status()

    # Parse the word from the RSS XML. The first item in the feed is today's word
    root = ET.fromstring(response.content)
    first_item = root.find(".//item")
    word = first_item.find("title").text.strip().lower()
    # word = "churlish" # DEBUG
    print(f"[{ts()}] WOTD from RSS: {word}")

    # Step 2: Get the sense index from dictionary (to use correct thesaurus sense)
    dict_result = mw_dict_tools.get_mw_dictionary_data(word)
    if dict_result and len(dict_result) >= 7:
        sense_idx = dict_result[6]  # 7th element is the sense index
    else:
        sense_idx = 0  # Default to first sense if dictionary lookup fails
    
    # Step 3: Look up synonyms via the Collegiate Thesaurus API using the correct sense
    synonyms = mw_dict_tools.get_mw_thesaurus_data(word, sense_idx)
    return word, synonyms

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
    word_tools = Word_Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)
    mw_dict_tools = MW_Dict_Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)
    wik_dict_tools = Wik_Dict_Tools(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)
    print(f"[{ts()}] Fetching Word of the Day and posting to Discord")
    no_post_mode = False  # DEBUG: set to True to run without posting to Discord
    if not no_post_mode: post_to_discord('https://www.merriam-webster.com/word-of-the-day', None)
    word, synonyms = get_wotd(mw_dict_tools)
    # print(f"[{ts()}] Word: {word}, Synonyms: {synonyms}") # DEBUG
    chart_buf = None
    filtered_out_synonyms = []  # Initialize for later use
    if not synonyms:
        print(f"[{ts()}] No synonyms found, cannot compare.")
        ngram_data = word_tools.get_ngrams_data([word])
        if ngram_data:
            chart_buf = word_tools.generate_chart(ngram_data, [word])
            wotd_freq = word_tools.get_recent_frequency(ngram_data, word)
            rarity = word_tools.get_rarity_label(wotd_freq)
            emoji = word_tools.get_frequency_tier_emoji(wotd_freq)
            commonality = f'{emoji} *{word}* is {rarity}. No thesaurus entry found — showing frequency over time only.'
        else:
            commonality = f'No thesaurus entry found for *{word}* — commonality data unavailable for today\'s word.'
    else:
        words = [word] + synonyms
        print(f"[{ts()}] Fetching Ngrams data for: {words}")
        ngram_data = word_tools.get_ngrams_data(words)

        if not ngram_data:
            print(f"[{ts()}] No Ngrams data found for {words}, cannot compare.")
            if not no_post_mode: post_to_discord(f'Not enough data to calculate commonality for "{word}".', None)
            print(f"[{ts()}] Posted to Discord successfully.")
        else:
            display_synonyms, filtered_out_synonyms, commonality = word_tools.build_insight(word, synonyms, ngram_data)
            chart_buf = word_tools.generate_chart(ngram_data, [word] + display_synonyms)

    ipa, regions = wik_dict_tools.get_wiktionary_data(word)
    pos, definition, example_sentence, etymology, audio_urls, prn, sense_idx, formality = mw_dict_tools.get_mw_dictionary_data(word)

    # Build insight in desired order: word+definition, pronunciation, example sentence, commonality, regional note
    insight_parts = []
    
    # Always add word + part of speech + definition
    if definition:
        insight_parts.append(f"**{word.capitalize()}** — *{pos}* — {definition}")
    else:
        insight_parts.append(f"**{word.capitalize()}** — *{pos}*")

    prn_disp = []
    if prn:
        prn_disp = ", ".join(prn) if len(prn) > 1 else prn[0]
    ipa_mw_disp = f" /{prn_disp}/ " if prn_disp else ''
    ipa_wi_disp = f" {ipa} " if ipa else ''

    if audio_urls:
        if len(audio_urls) == 1:
            insight_parts.append(f"🔊 Pronunciation:{ipa_wi_disp}{ipa_mw_disp}  🎵  [Audio Example]({audio_urls[0]})")
        else:
            audio_links = "  ".join([f"🎵  [Audio Example {i+1}]({url})" for i, url in enumerate(audio_urls)])
            insight_parts.append(f"🔊 Pronunciation:{ipa_wi_disp}{ipa_mw_disp}  {audio_links}")
    elif ipa:
        insight_parts.append(f"🔊 Pronunciation:{ipa_wi_disp}{ipa_mw_disp}")

    # Add example sentence if available
    if example_sentence:
        insight_parts.append(f"💬 Example: \"{example_sentence}\"")

    if regions:
        insight_parts.append(f"🌏 Regional note: primarily used in {', '.join(regions)}")
    
    if formality:
        insight_parts.append(f"🤵 Formality: {formality}")
    
    if etymology:
        print(f"[{ts()}] Etymology: {etymology}")
        insight_parts.append(etymology)
    else:
        print(f"[{ts()}] No etymology data found for {word}.")

    insight_parts.append(commonality)
    
    insight = "\n".join(insight_parts)
    
    # Add note about synonyms not plotted due to frequency disparity
    if filtered_out_synonyms:
        synonym_word = "Synonym" if len(filtered_out_synonyms) == 1 else "Synonyms"
        filtered_list = ", ".join(filtered_out_synonyms)
        insight += f"\n{synonym_word} not plotted: {filtered_list}"
    print(f"[{ts()}] Insight: {insight}")

    if not no_post_mode: post_to_discord(insight, chart_buf)

    print(f"[{ts()}] Posted to Discord successfully.")


if __name__ == "__main__":
    main()