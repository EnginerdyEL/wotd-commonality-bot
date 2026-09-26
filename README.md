# Wordy — WOTD Commonality Bot

A Discord automation that posts daily insights about the Merriam-Webster Word of the Day (WOTD), helping English learners understand how common the word is, how to pronounce it, where it's from, and more

## What it does

Every day, Wordy automatically:
1. Posts a link to the Merriam-Webster Word of the Day
2. Extracts the word and its short definition from the MW RSS feed's `<merriam:shortdef>` element
3. Posts the word, part of speech, and short definition from the RSS feed
4. Fetches the word's synonyms from the MW Collegiate Thesaurus API
5. Looks up and shares pronunciation in IPA format via Wiktionary API
6. Looks up and shares pronunciation in audio format via MW Collegiate Dictionary API
7. Extracts and shares an example sentence from MW Dictionary API
8. Looks up frequency data for the word via Google Ngrams
9. Posts a frequency-over-time chart on a logarithmic scale with the word plotted against reference baseline words (common, moderate, rare, very rare)
10. Displays up to 5 relevant synonyms (closest in frequency + most common)
11. Posts the etymology from the MW Collegiate Dictionary API
12. Posts formality indicator (slang, informal, etc.) when the word has non-standard register from MW Dictionary API
13. Posts regional indicators from Wiktionary when applicable

## Example Insight output

> **Speculate** — *verb* — to meditate on or ponder a subject
> 
> 🔊 Pronunciation: /ˈspek.jə.leɪt/  🎵 [Audio Example](https://...)
> 
> 💬 Example: "speculates whether it will rain all vacation"
>
> 🟡 "speculate" is moderately common and 15.5x less common than "guess" in literature.
>
> Synonyms: surmise, conjecture, theorize, guess, hypothesize

> **Yeet** — *verb* — to throw with force and without careful aim
>
> 🔊 Pronunciation: /jiːt/  🎵 [Audio Example](https://...)
>
> 💬 Example: "yeet that across the room"
>
> 🤵 Formality: Slang
>
> 🔴 "yeet" is very rare and 850x less common than "throw" in literature.
>
> Synonyms: throw, toss, fling, hurl, launch

> **Volition** — *noun* — the power of making a choice or decision
>
> 🟡 "volition" is uncommon and 5.2x less common than "autonomy" in literature.
>
> Synonyms: autonomy, choice, decision, preference, discretion

## Pronunciation

Pronunciation via IPA is pulled from Wiktionary, and pronunciation audio sample is pulled from MW Dictionary

## Word Definition

Wordy extracts the word's short definition directly from the Merriam-Webster WOTD RSS feed's `<merriam:shortdef>` element. This ensures consistency between the WOTD Discord embed and Wordy's output. The shortdef is curated by Merriam-Webster to match exactly what appears on their Word of the Day page, avoiding cases where API definitions pick the wrong sense or show unhelpful synonym definitions (e.g., "pandit" instead of the actual definition). If the RSS shortdef is unavailable, the bot falls back to the primary API definition. The part of speech is drawn from the MW Dictionary API.

## Example Sentence

An example sentence is extracted from the MW Collegiate Dictionary API when available. This provides immediate, learner-friendly usage context. Note that example quality varies—some clearly demonstrate the definition, while others simply show the word in use.

## Frequency Tier Emoji

A visual rarity indicator precedes the frequency comparison:
- 🟢 Common or very common
- 🟡 Moderately common or uncommon  
- 🔴 Rare or very rare

This allows learners to quickly gauge word rarity at a glance.

## Rarity tiers

Thresholds are empirically derived. See `calibration/calibrate.py` and `calibration/results.csv`.

These thresholds are hardcoded into `bot.py`, more details below

| Tier | Ngram frequency |
|---|---|
| Very Common | ≥ 0.0001% |
| Common | 0.00001% – 0.0001% |
| Moderately Common | 0.000001% – 0.00001% |
| Uncommon | 0.0000001% – 0.000001% |
| Rare | 0.00000001% – 0.0000001% |
| Very Rare | < 0.00000001% |

## Etymology

Etymology is pulled from MW Dictionary and reformatted for Discord, published after the rarity insight and graph

## Regional Indicator

Regional indicators are pulled from Wiktionary's wikitext API and published as part of the rarity insight line. Regions are listed in the order they appear in the Wiktionary entry. Currently tracked regions: Australia, New Zealand, British, UK, US, American, Canada, Canadian, Ireland, Irish, Scotland, Scottish. Hard-coded in bot.py

## Formality Indicator

Formality indicators help learners understand whether a word is typically used in casual speech or formal writing. Labels are pulled from the Merriam-Webster Collegiate Dictionary API when available. Non-standard registers are shown with emoji 🤵.

Possible indicators: Slang, Informal, Vulgar, and others. Standard/formal words (the majority) show no indicator by default to keep output clean. When formality is shown, it reflects the register of the definition sense being displayed (which may differ from other senses of the same word).

## Frequency Chart and Synonyms

**Logarithmic Scale Chart:** The frequency-over-time chart displays on a logarithmic scale with a baseline of reference words spanning common (e.g., "the", "house") to very rare (e.g., "incandescence"). This allows readers to see the word's absolute rarity position without distortion from outlier synonyms. The word-of-the-day is always plotted alongside these reference words, providing meaningful context for its frequency tier.

**Synonym Selection:** From all available synonyms, Wordy selects the closest 2 by frequency distance plus the 3 most common, up to 5 total. This balances showing semantically relevant words (closest in frequency) with common alternatives readers may already know (most frequent). Synonyms are listed as a simple comma-separated line ("Synonyms: a, b, c, d, e") to save space and let readers quickly identify alternatives at similar rarity levels.

## Tech stack

- **Python 3.14**
- **requests** — webhook posting
- **Merriam-Webster Collegiate Thesaurus API** — synonym lookup
- **Merriam-Webster Collegiate Dictionary API** — etymology and pronunciation lookup
- **Wiktionary API** — regional indicator and IPA lookup
- **Google Ngrams JSON endpoint** — frequency data
- **matplotlib** — chart generation
- **GitHub Actions** — daily scheduling (cron job)

## File Structure

Wordy is organized with separation of concerns across specialized tool classes:

- **bot.py** — Main entry point that orchestrates the Word of the Day workflow
- **mw_tools.py** — `MW_Tools` class handles Merriam-Webster Dictionary API (definitions, etymology, sense analysis), Thesaurus API (synonym lookup), and RSS feed shortdef extraction
- **word_tools.py** — `Word_Tools` class handles Google Ngrams frequency data, rarity labeling, and frequency charts
- **wik_dict_tools.py** — `Wik_Dict_Tools` class handles Wiktionary API for pronunciation (IPA) and regional indicators
- **tools.py** — Base `Tools` class with shared utilities (debugging, timestamps)
- **test_bot.py** — Unit tests for core dictionary and thesaurus extraction

## Setup

### Prerequisites
- Python 3.13+
- A Discord webhook URL for the target channel
- A Merriam-Webster Collegiate Dictionary API key - used for etymology lookup
- A Merriam-Webster Collegiate Thesaurus API key - used for synonym lookup

### Local development
```bash
git clone https://github.com/EnginerdyEL/wotd-commonality-bot.git
cd wotd-commonality-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the root directory (never commit this):
```
MW_DI_API_KEY=your_dictionary_key_here
MW_TH_API_KEY=your_thesaurus_key_here
DISCORD_WEBHOOK_URL=your_webhook_url_here
```

Then run:
```bash
python3 bot.py
```

#### No post mode

To run the script just on the command line without posting to Discord, set `no_post_mode = True` in `bot.py`

### Deployment

The bot runs via GitHub Actions on a daily cron schedule. Secrets are stored in the repository's Actions secrets — never in code.

To deploy to a new server, create a Discord webhook in the target channel and update the `DISCORD_WEBHOOK_URL` secret in GitHub.

## Testing

Run the unit test suite with:
```bash
python3 test_bot.py
```

This tests dictionary and thesaurus extraction across 7 edge cases including accented characters, rare words, multi-word phrases, and multiple pronunciations.

### Regression Testing Strategy

A separate etymology test suite (`etymology_test_cases.json` and `test_etymology()`) validates that markup parsing doesn't regress as regex patterns evolve. Known limitations exist around complex markup patterns - see Future Ideas below.

To add test cases, edit `TEST_CASES` in `test_bot.py` or add entries to `etymology_test_cases.json` for etymology-specific tests.

## Cron schedule

Scheduled for 5:30 AM UTC daily (`30 5 * * *`), which corresponds to:
- 12:30 AM ET in winter (EST, UTC-5)
- 1:30 AM ET in summer (EDT, UTC-4)

Note: GitHub Actions free tier may delay execution by 2-3 hours. The job is intended to post sometime after midnight ET when the Merriam Webster RSS feed is updated

## Calibration

To recalibrate the rarity thresholds:
```bash
cd calibration
python3 calibrate.py
```

This generates `results.csv` with ngram frequencies for 40 reference words across four tiers. Open in a spreadsheet, sort by frequency, and adjust the thresholds in `get_rarity_label()` in `bot.py` as needed.

### Spot check mode

To quickly check specific words without overwriting `results.csv`, set `SPOT_CHECK_MODE = True` in `calibrate.py` and add your words to `SPOT_CHECK_WORDS`. This will print each word's ngram frequency, rarity tier, and any regional indicators from Wiktionary — useful for investigating a specific WOTD or its synonyms or any other set of words.

## Known Limitations

- Etymology and example sentence markup parsing relies on regex chains, which can be fragile with complex MW API markup. A regression test suite tracks this, but manual review is sometimes needed for edge cases.
- Synonym selection prioritizes semantic relevance by skipping archaic/obsolete senses. However, when multiple current senses exist, the thesaurus API doesn't indicate which is most relevant, so frequency-based ranking is used as a tie-breaker.

## Future ideas

### Near term

- Clean up tech debt of old ways to pull the definition and extract relevant synonyms
- Add "Recent Examples on the Web" — extract from MW dictionary page if available in API, or fetch multiple example sentences and select the most illustrative
- Add a "rhymes with" section, pulled from Datamuse API with frequency-based filtering
- Add a "phrases" section, pulled from MW API if available
- Investigate colloquial vs. literary tags in Wiktionary to enrich formality indicators beyond MW's current coverage

### Longer term

- Consider `mwparserfromhell` library for cleaner markup parsing if regex fragility becomes unmanageable
- Slash commands for on-demand word lookup (requires hosting the bot)
- Multi-server support via multiple webhooks
- Spellcheck suggestions for unrecognized words (only relevant if on-demand available)