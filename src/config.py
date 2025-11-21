"""Configuration management for the Discord bot."""
import os
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()


class Config:
    """Bot configuration loaded from environment variables."""

    # Discord settings
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    GUILD_ID = int(os.getenv('GUILD_ID', 0))
    SHARED_CHANNEL_ID = int(os.getenv('SHARED_CHANNEL_ID', 0))

    # Supabase settings
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    # Google Gemini settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')

    # Bot settings
    DAILY_WORD_REQUIREMENT = int(os.getenv('DAILY_WORD_REQUIREMENT', 500))
    TIMEZONE = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        required = {
            'DISCORD_BOT_TOKEN': cls.DISCORD_BOT_TOKEN,
            'GUILD_ID': cls.GUILD_ID,
            'SHARED_CHANNEL_ID': cls.SHARED_CHANNEL_ID,
            'SUPABASE_URL': cls.SUPABASE_URL,
            'SUPABASE_KEY': cls.SUPABASE_KEY,
            'GEMINI_API_KEY': cls.GEMINI_API_KEY,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True
