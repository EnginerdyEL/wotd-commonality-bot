# Wordy — WOTD Commonality Bot

A Discord automation that posts daily insights about the Merriam-Webster Word of the Day (WOTD), helping English learners understand how common or rare the word is relative to its closest synonyms.

## What it does

Every day, Wordy automatically:
1. Posts a link to the Merriam-Webster Word of the Day
2. Posts the word, part of speech, and primary definition from MW Dictionary API
3. Fetches the word's synonyms from the MW Collegiate Thesaurus API
4. Looks up and shares pronunciation in IPA format via Wiktionary API
5. Looks up and shares pronunciation in audio format via MW Collegiate Dictionary API
6. Extracts and shares an example sentence from MW Dictionary API
7. Looks up frequency data for the word and its common synonyms via Google Ngrams
8. Posts an insight with frequency tier emoji, examples below
9. Posts a frequency-over-time chart showing the word and synonyms plotted from 1900–2019
10. Posts the etymology from the MW Collegiate Dictionary API

If no thesaurus entry exists for the word, it posts the rarity label and frequency chart for the word alone.

## Example Insight output

> **Speculate** — *verb* — to meditate on or ponder a subject
> 
> 🔊 Pronunciation: /ˈspek.jə.leɪt/  🎵 [Audio Example](https://...)
> 
> 💬 Example: "speculates whether it will rain all vacation"
>
> 🟡 "speculate" is moderately common and 15.5x less common than "guess" in literature.

> **Adroit** — *adjective* — having or showing skill, cleverness, or resourcefulness in handling situations
>
> 🔊 Pronunciation: /əˈdɹɔɪt/  🎵 [Audio Example](https://...)
>
> 💬 Example: "an adroit negotiator"
>
> 🟡 "adroit" is uncommon and 75.1x less common than "expert" in literature.

> **Evanescent** — *adjective* — tending to vanish like vapor
>
> 🟡 "evanescent" is uncommon and 79.7x less common than "brief" in literature.

## Pronunciation

Pronunciation via IPA is pulled from Wiktionary, and pronunciation audio sample is pulled from MW Dictionary

## Word Definition

The word, part of speech, and primary definition are extracted from the MW Collegiate Dictionary API. This ensures learners get the authoritative first definition without needing to click the Merriam-Webster link.

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

Regional indicators are pulled from Wiktionary's wikitext API and published as part of the rarity insight line. Regions are listed in the order they appear in the Wiktionary entry.
Currently tracked regions: Australia, New Zealand, British, UK, US, American, Canada, Canadian, Ireland, Irish, Scotland, Scottish. Hard-coded in bot.py

## Tech stack

- **Python 3.14**
- **requests** — webhook posting
- **Merriam-Webster Collegiate Thesaurus API** — synonym lookup
- **Merriam-Webster Collegiate Dictionary API** — etymology and pronunciation lookup
- **Wiktionary API** — regional indicator and IPA lookup
- **Google Ngrams JSON endpoint** — frequency data
- **matplotlib** — chart generation
- **GitHub Actions** — daily scheduling (cron job)

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

## Future ideas

### Near term

- Dev improvement: Make the Debug flag accessible via command-line
- Dev improvement: Add a unit test for happy path and several edge cases, essentially running several words through the functions to flag if any errors were hit, and without posting to Discord
- Fix condition where synonym is so relatively common that it makes the wotd appear as a flatline on the chart. Perhaps only plot when within some factor of each other
- Improve example sentences: either extract multiple examples and pick the best, or use Claude to generate more illustrative examples
- Clean up definition, example, and etymology markup parsing using `mwparserfromhell` library instead of unreliable regex chains
- Delay the Github Action so that if the MW embed is late or the Discord embed is cached incorrectly, then the wotd embed is more likely to be correct

### Longer term

- Slash commands for on-demand lookup of any word, requiring hosting the bot
- Multi-server support via multiple webhooks
- Spellcheck suggestions for unrecognized words, if on-demand is supported