# Wordy — WOTD Commonality Bot

A Discord automation that posts daily insights about the Merriam-Webster Word of the Day (WOTD), helping English learners understand how common the word is, how to pronounce it, where it's from, and more

## What it does

Every day, Wordy automatically:
1. Posts a link to the Merriam-Webster Word of the Day
2. Posts the word, part of speech, and primary definition from MW Dictionary API
3. Fetches the word's synonyms from the MW Collegiate Thesaurus API
4. Looks up and shares pronunciation in IPA format via Wiktionary API
5. Looks up and shares pronunciation in audio format via MW Collegiate Dictionary API
6. Extracts and shares an example sentence from MW Dictionary API
7. Looks up frequency data for the word and its common synonyms via Google Ngrams
8. Filters synonyms by similar frequency to prevent flatline charts
9. Posts an insight with frequency tier emoji and rarity comparison
10. Posts a frequency-over-time chart showing the word and filtered synonyms plotted from 1900–2019
11. Posts the etymology from the MW Collegiate Dictionary API
12. Posts formality indicator (slang, informal, etc.) when the word has non-standard register from MW Dictionary API
13. Posts regional indicators from Wiktionary when applicable

If no thesaurus entry exists for the word, it posts the rarity label and frequency chart for the word alone.

## Example Insight output

> **Speculate** — *verb* — to meditate on or ponder a subject
> 
> 🔊 Pronunciation: /ˈspek.jə.leɪt/  🎵 [Audio Example](https://...)
> 
> 💬 Example: "speculates whether it will rain all vacation"
>
> 🟡 "speculate" is moderately common and 15.5x less common than "guess" in literature.

> **Yeet** — *verb* — to throw with force and without careful aim
>
> 🔊 Pronunciation: /jiːt/  🎵 [Audio Example](https://...)
>
> 💬 Example: "yeet that across the room"
>
> 🤵 Formality: Slang
>
> 🔴 "yeet" is very rare and 850x less common than "throw" in literature.

> **Volition** — *noun* — the power of making a choice or decision
>
> 🟡 "volition" is uncommon and 5.2x less common than "autonomy" in literature.
>
> Synonyms not plotted: accord, will

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

Regional indicators are pulled from Wiktionary's wikitext API and published as part of the rarity insight line. Regions are listed in the order they appear in the Wiktionary entry. Currently tracked regions: Australia, New Zealand, British, UK, US, American, Canada, Canadian, Ireland, Irish, Scotland, Scottish. Hard-coded in bot.py

## Formality Indicator

Formality indicators help learners understand whether a word is typically used in casual speech or formal writing. Labels are pulled from the Merriam-Webster Collegiate Dictionary API when available. Non-standard registers are shown with emoji 🤵.

Possible indicators: Slang, Informal, Vulgar, and others. Standard/formal words (the majority) show no indicator by default to keep output clean. When formality is shown, it reflects the register of the definition sense being displayed (which may differ from other senses of the same word).

## Ngrams Display and Synonym Filtering

To prevent the word-of-the-day from appearing as a flatline on the chart when a synonym is significantly more or less common, Wordy filters synonyms before display:

- **Threshold:** Only synonyms within 0.2x to 5x the word's frequency are displayed on the chart
- **Display limit:** Up to 3 filtered synonyms are plotted alongside the word
- **All synonyms considered:** The bot evaluates all available synonyms, not just the top 3
- **Comparison always shown:** The rarity comparison in the insight text uses the most common synonym overall (even if it's filtered out of the chart), ensuring learners always see a meaningful frequency ratio

Synonyms filtered out due to frequency disparity are listed at the bottom of the insight ("Synonyms not plotted: ...") so learners know other options exist but are too common or rare to plot meaningfully.

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

- Add "Recent Examples on the Web" — extract from MW dictionary page if available in API, or fetch multiple example sentences and select the most illustrative
- Add a "rhymes with" section, pulled from Datamuse API with frequency-based filtering
- Add a "phrases" section, pulled from MW API if available
- Investigate colloquial vs. literary tags in Wiktionary to enrich formality indicators beyond MW's current coverage

### Longer term

- Consider `mwparserfromhell` library for cleaner markup parsing if regex fragility becomes unmanageable
- Slash commands for on-demand word lookup (requires hosting the bot)
- Multi-server support via multiple webhooks
- Spellcheck suggestions for unrecognized words (only relevant if on-demand available)