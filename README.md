# Wordy — WOTD Commonality Bot

A Discord automation that posts daily insights about the Merriam-Webster Word of the Day (WOTD), helping English learners understand how common or rare the word is relative to its closest synonyms.

## What it does

Every day, Wordy automatically:
1. Posts a link to the Merriam-Webster Word of the Day
2. Fetches the word's synonyms from the MW Collegiate Thesaurus API
3. Looks up and shares pronunciation in IPA format via Wiktionary API
4. Looks up and shares pronunciation in audio format via MW Collegiate Dictionary API
5. Looks up frequency data for the word and its common synonyms via Google Ngrams
6. Posts an insight, examples below
7. Posts a frequency-over-time chart showing the word and synonyms plotted from 1900–2019
8. Posts the etymology from the MW Collegiate Dictionary API

If no thesaurus entry exists for the word, it posts the rarity label and frequency chart for the word alone.

## Example Insight output

> 🔊 Pronunciation: /ʃɪˈnæn.ɪ.ɡənz/
> 🎵 Audio: https://media.merriam-webster.com/audio/prons/en/us/mp3/s/shenan01.mp3
> "shenanigans" is uncommon and 9.7x less common than "mischief" in literature.

> "adroit" is uncommon and 75.1x less common than "expert" in literature.

> "erin go bragh" is very rare. No thesaurus entry found — showing frequency over time only.

## Pronunciation

Pronunciation via IPA is pulled from Wiktionary, and pronunciation audio sample is pulled from MW Dictionary

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

- Fix condition where synonym is so relatively common that it makes the wotd appear as a flatline on the chart. Perhaps only plot when within some factor of each other
- Clean up etymology markup parsing using `mwparserfromhell` library instead of unreliable regex chains
- Slash commands for on-demand lookup of any word, requiring hosting the bot
- Multi-server support via multiple webhooks
- Spellcheck suggestions for unrecognized words, if on-demand is supported
