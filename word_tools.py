import io
import requests
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from datetime import datetime
from tools import Tools

# This class handles other functions related to the word of the day
class Word_Tools(Tools):

    def __init__(self, DEBUG, MW_DI_API_KEY, MW_TH_API_KEY):
        super().__init__(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)


    def get_frequency_tier_emoji(self, frequency):
        """Return a frequency tier emoji based on rarity label."""
        if frequency >= 1e-4:
            return "🟢"  # very common
        elif frequency >= 1e-5:
            return "🟢"  # common
        elif frequency >= 1e-6:
            return "🟡"  # moderately common
        elif frequency >= 1e-7:
            return "🟡"  # uncommon
        elif frequency >= 1e-8:
            return "🔴"  # rare
        else:
            return "🔴"  # very rare


    def get_ngrams_data(self, words):
        """Fetch frequency data from Google Ngrams for a list of words."""
        content = ",".join(words)
        url = (
            f"https://books.google.com/ngrams/json"
            f"?content={content}"
            f"&year_start={self.NGRAMS_START_YEAR}"
            f"&year_end={self.NGRAMS_END_YEAR}"
            f"&corpus=en-2019"
            f"&smoothing=3"
        )
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


    def get_recent_frequency(self, ngram_data, word):
        """Get the average frequency of a word over the last 10 years of data."""
        for entry in ngram_data:
            if entry["ngram"].lower() == word.lower():
                recent = entry["timeseries"][-10:]
                return sum(recent) / len(recent) if recent else 0
        return 0


    def get_rarity_label(self, frequency):
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


    def generate_chart(self, wotd):
        """Generate a frequency chart image and return it as bytes."""
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 8))
        # Baseline words for comparison
        words = ["the", "house", "apple", "cushion", "thimble", "incandescence", wotd]
        ngram_data = self.get_ngrams_data(words)
    
        for entry in ngram_data:
            if entry["ngram"].lower() in [w.lower() for w in words]:
                years = list(range(self.NGRAMS_START_YEAR, self.NGRAMS_END_YEAR + 1))
                ax.plot(years, entry["timeseries"], label=entry["ngram"])

        ax.set_title("Word Frequency Over Time (Google Ngrams)", fontsize='20')
        ax.set_xlabel("Year", fontsize="x-large")
        ax.set_ylabel("Frequency (%)", fontsize="x-large")
        ax.set_yscale("log")
        ax.legend(fontsize='x-large')
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.6f}%'))
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        buf.seek(0)
        plt.close()
        return buf

    def build_insight(self, word, synonyms, ngram_data):
        """Build the insight text comparing the WOTD to its best synonym.
        Selects closest 2 + most common 3 synonyms for display (5 total max).
        Always uses best overall synonym for comparison in insight text."""
        if not ngram_data:
            return [], "Not enough data to calculate commonality."

        wotd_freq = self.get_recent_frequency(ngram_data, word)
        if wotd_freq == 0:
            return [], "Not enough data to calculate commonality."
        
        # Calculate frequencies for all synonyms
        syn_freqs = {s: self.get_recent_frequency(ngram_data, s) for s in synonyms}
        
        # Find the best (most common) synonym overall for the comparison line
        best_syn = max(synonyms, key=lambda s: syn_freqs[s])
        best_syn_freq = syn_freqs[best_syn]
        
        # Find closest 2 synonyms by frequency distance from WOTD
        closest_2 = sorted(
            syn_freqs.items(),
            key=lambda x: abs(x[1] - wotd_freq)
        )[:2]
        closest_2_names = [s for s, _ in closest_2]
        
        # Start with closest 2
        selected_synonyms = closest_2_names.copy()
        
        # Fill remaining slots (up to 5 total) with most common that aren't already selected
        most_common_sorted = sorted(
            syn_freqs.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for syn, _ in most_common_sorted:
            if len(selected_synonyms) >= 5:
                break
            if syn not in selected_synonyms:
                selected_synonyms.append(syn)
        print(f"[{self.ts()}] Selected Synonyms: {selected_synonyms}")
        
        # Build the commonality comparison using the best synonym overall
        rarity = self.get_rarity_label(wotd_freq)
        emoji = self.get_frequency_tier_emoji(wotd_freq)

        if wotd_freq >= best_syn_freq:
            ratio = wotd_freq / best_syn_freq
            if ratio < 1.5:
                commonality = f'{emoji} *{word}* is {rarity} and about as common as *{best_syn}* in literature.'
            else:
                commonality = f'{emoji} *{word}* is {rarity} and {ratio:.1f}x more common than *{best_syn}* in literature.'
        else:
            ratio = best_syn_freq / wotd_freq
            if ratio < 1.5:
                commonality = f'{emoji} *{word}* is {rarity} and about as common as *{best_syn}* in literature.'
            else:
                commonality = f'{emoji} *{word}* is {rarity} and {ratio:.1f}x less common than *{best_syn}* in literature.'
        
        return selected_synonyms, commonality