import xml.etree.ElementTree as ET
from datetime import datetime

# Superclass for the child tool classes
# This class handles the debug logic and handles the API keys for the child tool classes
class Tools:

    NGRAMS_START_YEAR = 1900
    NGRAMS_END_YEAR = 2019

    def __init__(self, DEBUG, MW_DI_API_KEY, MW_TH_API_KEY):
        self.DEBUG = DEBUG
        self.MW_DI_API_KEY = MW_DI_API_KEY
        self.MW_TH_API_KEY = MW_TH_API_KEY

    def ts(self):
        """Return current timestamp string for logging."""
        return (f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}")[:-5]

    def debug(self, message):
        """Print debug message only if DEBUG flag is True."""
        if self.DEBUG:
            print(f"[{self.ts()}] DEBUG: {message}")