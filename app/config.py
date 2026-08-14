import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    WC_URL: str = os.getenv("WC_URL", "https://www.maat.ae")
    WC_CK: str = os.getenv("WC_CK", "")
    WC_CS: str = os.getenv("WC_CS", "")
    PORT: int = int(os.getenv("PORT", 8000))

settings = Settings()