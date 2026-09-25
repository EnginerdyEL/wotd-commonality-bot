import re
import requests
import xml.etree.ElementTree as ET
from unidecode import unidecode
from urllib.parse import quote
from tools import Tools

# This class handles the functions that interact with Merriam-Webster
class MW_Tools(Tools):

    def __init__(self, DEBUG, MW_DI_API_KEY, MW_TH_API_KEY):
        super().__init__(DEBUG, MW_DI_API_KEY, MW_TH_API_KEY)

    def get_mw_thesaurus_data(self, word, target_sense_idx=0):
            """Fetch synonyms from the MW Collegiate Thesaurus API.
            
            Args:
                word: The word to look up
                target_sense_idx: Which sense group to use (0-based index). Default 0 = first sense.
            
            Returns:
                List of synonyms from the target sense group
            """
            api_url = f"https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{quote(word)}?key={self.MW_TH_API_KEY}"

            api_response = requests.get(api_url)
            api_response.raise_for_status()
            data = api_response.json()

            synonyms = []
            for entry in data:
                if isinstance(entry, dict) and "meta" in entry:
                    meta = entry["meta"]
                    syn_groups = meta.get("syns", [])
                    
                    self.debug(f"Thesaurus for '{word}': found {len(syn_groups)} sense group(s)")
                    self.debug(f"  Using sense index {target_sense_idx}")
                    
                    # Use only the target sense group
                    if target_sense_idx < len(syn_groups):
                        syn_list = syn_groups[target_sense_idx]
                        self.debug(f"  Sense {target_sense_idx}: {len(syn_list)} synonym(s)")
                        for syn in syn_list:
                            if syn.lower() != word.lower() and syn.lower() not in synonyms:
                                synonyms.append(re.sub(r'[()]', '', syn).lower().strip())
                    else:
                        self.debug(f"  WARNING: Requested sense index {target_sense_idx} but only {len(syn_groups)} sense(s) available. Using sense 0.")
                        if syn_groups:
                            for syn in syn_groups[0]:
                                if syn.lower() != word.lower() and syn.lower() not in synonyms:
                                    synonyms.append(re.sub(r'[()]', '', syn).lower().strip())
                    
                    break  # only use first dictionary entry
            
            self.debug(f"Collected {len(synonyms)} unique synonym(s) from sense {target_sense_idx}")
            return synonyms


    def get_mw_dictionary_data(self, word):
        """Fetch definition, part of speech, etymology, example sentence, and audio pronunciation URL from the MW Collegiate Dictionary API."""
        api_url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{quote(unidecode(word))}?key={self.MW_DI_API_KEY}"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        self.debug(f"API response type: {type(data)}, length: {len(data) if isinstance(data, list) else 'N/A'}")
        if isinstance(data, list) and len(data) > 0:
            self.debug(f"First item type: {type(data[0])}")

        if not data or not isinstance(data[0], dict):
            self.debug(f"API returned empty/malformed response for '{word}': {data}")
            return None, None, None, None, None, None

        # Always use first entry for POS, pronunciation, and audio (most complete phonetic data)
        first_entry = data[0]
        
        # Loop through entries to find the one with the best definition (prefer current over obsolete/archaic)
        definition_entry = None
        fallback_entry = None
        best_sense_idx = 0  # Track which sense index is the best (0-based)
        
        for candidate in data:
            if not isinstance(candidate, dict):
                continue
            
            # Check if this entry has any non-obsolete/archaic definitions
            defs = candidate.get('def', [])
            has_current = False
            current_sense_idx = 0  # Track sense index within this search
            
            if defs:
                for def_block in defs:
                    sseq = def_block.get('sseq', [])
                    sense_idx = 0  # Counter for sense groups
                    for sense_group in sseq:
                        if isinstance(sense_group, list):
                            for sense_item in sense_group:
                                if isinstance(sense_item, list) and len(sense_item) >= 2:
                                    sense_data = sense_item[1]
                                    if isinstance(sense_data, dict):
                                        sls = sense_data.get('sls', [])
                                        is_obsolete = 'obsolete' in sls if isinstance(sls, list) else False
                                        is_archaic = 'archaic' in sls if isinstance(sls, list) else False
                                        if not (is_obsolete or is_archaic):
                                            has_current = True
                                            current_sense_idx = sense_idx
                                            break
                                sense_idx += 1
                            if has_current:
                                break
                    if has_current:
                        break
            
            # Use first entry with current definitions
            if has_current:
                definition_entry = candidate
                best_sense_idx = current_sense_idx
                break
            # Or save first entry as fallback if all are obsolete/archaic
            elif not fallback_entry:
                fallback_entry = candidate
        
        # Use fallback if no current definitions found
        if not definition_entry:
            definition_entry = fallback_entry
            best_sense_idx = 0
        
        if not definition_entry:
            self.debug(f"No valid entry found for '{word}'")
            return None, None, None, None, None, None, 0
        
        # DEBUG: Print the entry structures
        self.debug(f"First entry keys: {first_entry.keys()}")
        self.debug(f"Definition entry keys: {definition_entry.keys()}")
        if 'def' in definition_entry:
            self.debug(f"def structure: {definition_entry['def']}")

        # Extract part of speech from first entry (most reliable)
        pos = first_entry.get('fl', 'word')  # 'fl' is functional label (part of speech)

        # Extract definition (from best sense index with current definitions)
        definition = None
        formality = None  # Will be set when we extract the definition
        defs = definition_entry.get('def', [])
        
        if defs:
            # Navigate the nested structure to find the definition at best_sense_idx
            sense_counter = 0
            for def_block in defs:
                sseq = def_block.get('sseq', [])
                for sense_group in sseq:
                    if isinstance(sense_group, list):
                        for sense_item in sense_group:
                            # sense_item is a list like ['sense', {sense_data}]
                            if isinstance(sense_item, list) and len(sense_item) >= 2:
                                sense_data = sense_item[1]  # Get the dict part
                                if isinstance(sense_data, dict):
                                    # Check if this is the best sense we identified
                                    if sense_counter == best_sense_idx:
                                        # This is the sense we want! Extract its definition and formality
                                        dt = sense_data.get('dt', [])
                                        self.debug(f"Extracting definition from sense index {sense_counter}")
                                        self.debug(f"Found dt array: {dt}")
                                        
                                        # Extract register/formality info (sls - sense-level status)
                                        # Check both def_block level and sense_data level (yeet has it at def_block level)
                                        sls_from_block = def_block.get('sls', [])
                                        sls_from_sense = sense_data.get('sls', [])
                                        sls = sls_from_block + sls_from_sense  # Combine both if they exist
                                        
                                        register_labels = []
                                        if isinstance(sls, list):
                                            for label in sls:
                                                # Skip archaic/obsolete (already filtered), include all other registers
                                                if label not in ['archaic', 'obsolete']:
                                                    # Capitalize for display: 'slang' -> 'Slang'
                                                    register_labels.append(label.capitalize())
                                        
                                        # Format formality: show only if non-standard register exists
                                        if register_labels:
                                            formality = ', '.join(register_labels)
                                        self.debug(f"Extracted formality: {formality}")
                                        
                                        if dt:
                                            for dt_item in dt:
                                                self.debug(f"dt_item: {dt_item}")
                                                if isinstance(dt_item, list) and len(dt_item) >= 2:
                                                    if dt_item[0] == 'text':
                                                        definition = dt_item[1]
                                                        self.debug(f"Extracted text definition: {definition}")
                                                        break
                                        if definition:
                                            break
                                sense_counter += 1
                        if definition:
                            break
                if definition:
                    break
        
        # Clean up definition markup if found
        if definition:
            # Merriam-Webster API markup patterns:
            # {d_link|word|...} — definition link
            # {sx|word||...} — cross-reference/synonym  
            # {dxt|word||...} — definition text reference
            # {it}text{/it} — italics
            # {bc} — "begin concept" marker
            # {dx_def}...{/dx_def} — definition cross-reference section
            
            # Extract words from link markup BEFORE removing braces
            definition = re.sub(r'\{d_link\|([^|]+)\|[^}]*\}', r'\1', definition)
            definition = re.sub(r'\{sx\|([^|]+)\|\|[^}]*\}', r'\1', definition)
            definition = re.sub(r'\{dxt\|([^|]+)\|[^|]*\|[^}]*\}', r'\1', definition)
            definition = re.sub(r'\{dx_def\}.*?\{/dx_def\}', '', definition)
            
            # Convert italics and remove other markup
            definition = re.sub(r'\{it\}(.*?)\{/it\}', r'*\1*', definition)
            definition = re.sub(r'\{bc\}', '', definition)
            definition = re.sub(r'\{[^}]+\}', '', definition)
            definition = definition.strip()
            definition = re.sub(r' +', ' ', definition)
            self.debug(f"Cleaned definition: {definition}")
        else:
            print(f"[{self.ts()}] WARNING: Could not extract definition for {word}")

        # Extract first example sentence - search across ALL def_blocks and senses (from definition_entry)
        example_sentence = None
        defs = definition_entry.get('def', [])
        for def_block in defs:
            if example_sentence:
                break
            sseq = def_block.get('sseq', [])
            for sense_group in sseq:
                if example_sentence:
                    break
                if isinstance(sense_group, list):
                    for sense_item in sense_group:
                        # sense_item is a list like ['sense', {sense_data}]
                        if isinstance(sense_item, list) and len(sense_item) >= 2:
                            # Safely get sense_data
                            if sense_item[0] != 'sense':
                                continue
                            sense_data = sense_item[1] if isinstance(sense_item[1], dict) else None
                            if not sense_data:
                                continue
                                
                            # Look for 'vis' in the dt array
                            dt = sense_data.get('dt', [])
                            if dt and isinstance(dt, list):
                                for dt_item in dt:
                                    if isinstance(dt_item, list) and len(dt_item) >= 2:
                                        if dt_item[0] != 'vis':
                                            continue
                                        vis_list = dt_item[1] if isinstance(dt_item[1], list) else None
                                        if not vis_list or len(vis_list) == 0:
                                            continue
                                        
                                        # Safely get first example
                                        first_example = vis_list[0] if isinstance(vis_list[0], dict) else None
                                        if first_example and 't' in first_example:
                                            example_sentence = first_example['t']
                                            # Clean up markup
                                            example_sentence = re.sub(r'\{it\}(.*?)\{/it\}', r'*\1*', example_sentence)
                                            example_sentence = re.sub(r'\{wi\}(.*?)\{/wi\}', r'*\1*', example_sentence)
                                            example_sentence = re.sub(r'\{[^}]+\}', '', example_sentence)
                                            example_sentence = example_sentence.strip()
                                            break
                            if example_sentence:
                                break
                        if example_sentence:
                            break
        
        if not example_sentence:
            print(f"[{self.ts()}] WARNING: Could not extract example sentence for {word}")

        # Extract etymology (from definition_entry)
        etymology = None
        et = definition_entry.get('et', None)
        if et:
            text = ""
            for item in et:
                if item[0] == 'text':
                    text = item[1]
                    break
            if text:
                self.debug(f"Etymology raw text before cleanup: {text[:200]}")
                # Use same markup patterns as definition cleanup (see above)
                text = re.sub(r'\{it\}(.*?)\{/it\}', r'*\1*', text)
                
                # Extract d_link content: {d_link|word|...} → word
                text = re.sub(r'\{d_link\|([^|]+)\|[^}]*\}', r'\1', text)
                
                # Handle dx_ety pattern BEFORE generic dxt extraction
                # Format: {dx_ety}see {dxt|word:num||}{/dx_ety} → — see word entry num
                dx_ety_match = re.search(r'\{dx_ety\}see \{dxt\|([^|:]+):(\d+)\|\|\}\{/dx_ety\}', text)
                if dx_ety_match:
                    word_ref = dx_ety_match.group(1)
                    entry_num = dx_ety_match.group(2)
                    self.debug(f"Found dx_ety pattern: word='{word_ref}', entry='{entry_num}'")
                    replacement = f'— see {word_ref} entry {entry_num}'
                    text = text.replace(dx_ety_match.group(0), replacement)
                else:
                    # Remove dx_ety if we couldn't parse it
                    text = re.sub(r'\{dx_ety\}.*?\{/dx_ety\}', '', text)
                
                # Extract dxt content: {dxt|word|...} → word (for non-dx_ety patterns)
                text = re.sub(r'\{dxt\|([^|:]+)(?::[^\|]*)?\|[^|]*\|[^}]*\}', r'\1', text)
                
                # Handle et_link: format varies - {et_link|word|variant}
                # Examples: {et_link|colloquy|colloquy}, {et_link|-al:1|-al:1}, {et_link|scruple|2}
                # Important: if both params are identical, just remove the tag (text is already mentioned)
                et_link_matches = re.findall(r'\{et_link\|([^|]+)\|([^}]+)\}', text)
                self.debug(f"Found {len(et_link_matches)} et_link match(es): {et_link_matches}")
                
                if et_link_matches:
                    for ref_word, ref_variant in et_link_matches:
                        if ref_word == ref_variant:
                            # Check if there's a preceding italic version of this word
                            # Extract just the word part (without :number suffix)
                            word_only = ref_word.split(':')[0]
                            italic_pattern = f'{{it}}{word_only}{{/it}}'
                            tag_position = text.find(f'{{et_link|{ref_word}|{ref_variant}}}')
                            preceding_text = text[max(0, tag_position - 100):tag_position]
                            
                            if italic_pattern in preceding_text or f'{{it}}' in preceding_text:
                                # Preceding italic found: remove the duplicate tag
                                text = text.replace(f'{{et_link|{ref_word}|{ref_variant}}}', '')
                            else:
                                # No preceding italic: extract the word
                                replacement = word_only
                                text = text.replace(f'{{et_link|{ref_word}|{ref_variant}}}', replacement)
                        else:
                            is_prefix = ref_word.startswith('-')
                            digit_match = re.search(r'(\d+)', ref_variant)
                            
                            if not is_prefix and digit_match:
                                # Full word with entry number → "— see word entry number"
                                entry_num = digit_match.group(1)
                                replacement = f'— see {ref_word} entry {entry_num}'
                            else:
                                # Prefix or no digit → just extract word/prefix
                                replacement = ref_word.split(':')[0] if ':' in ref_word else ref_word
                            
                            text = text.replace(f'{{et_link|{ref_word}|{ref_variant}}}', replacement)
                # Remove any et_link that couldn't be parsed (malformed)
                text = re.sub(r'\{et_link\|.*?\}', '', text)
                
                # Remove "more at" references: {ma}{mat|...}{/ma}
                text = re.sub(r'\{ma\}\{mat\|(.*?)\|.*?\}\{/ma\}', '', text)
                
                # Remove any remaining markup
                text = re.sub(r'\{[^}]+\}', '', text)
                text = re.sub(r' +', ' ', text)
                text = text.strip()
                self.debug(f"Etymology cleaned text: {text}")
                etymology = f'📖 **Etymology of *{word}*:** {text}'

        # Extract audio URLs and pronunciations from first entry (best phonetic data)
        audio_urls = []
        prn = []
        prs = first_entry.get('hwi', {}).get('prs', [])
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
            if 'mw' in pr:
                mw = pr['mw']
                prn.append(mw)
        self.debug(f"pronunciation = {prn}")
        self.debug(f"Best sense index for '{word}': {best_sense_idx}")
        self.debug(f"Formality: {formality}")
        
        # Extract shortdef from API response
        api_shortdef = None
        if first_entry and 'shortdef' in first_entry:
            shortdef_list = first_entry['shortdef']
            if isinstance(shortdef_list, list) and len(shortdef_list) > 0:
                api_shortdef = shortdef_list[0]  # Get first shortdef
                self.debug(f"Extracted shortdef from API: {api_shortdef[:100]}")

        return pos, definition, example_sentence, etymology, audio_urls if audio_urls else None, prn if prn else None, best_sense_idx, formality, api_shortdef