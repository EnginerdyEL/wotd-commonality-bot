import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from tools import Tools

# This class handles the functions that interact with Wiktionary
class Wik_Dict_Tools(Tools):

    def __init__(self, DEBUG, MW_DI_API_KEY, MW_TH_API_KEY):
        super().__init__(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)

    def get_wiktionary_data(self, word):
        """Fetch regional/usage labels and IPA pronunciation from Wiktionary."""
        headers = {'User-Agent': 'WOTDCommonalityBot/1.0 (educational Discord bot; contact via GitHub)'}
        url = f"https://en.wiktionary.org/w/api.php?action=parse&page={quote(word)}&prop=wikitext&format=json"
        try:
            response = requests.get(url, headers=headers, timeout=5)
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
            if not ipa:
                print(f"[{self.ts()}] Warning: No IPA found for {word}")

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
        except requests.RequestException as e:
            print(f"[{self.ts()}] Wiktionary lookup failed for {word}: {e}")
            return None, None