"""Main Discord bot implementation."""
import discord
from discord.ext import commands
import logging
from src.config import Config
from src.database import Database
from src.plugin_base import PluginManager
from src.plugins.journaling import JournalingPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DiscordBot(commands.Bot):
    """Main Discord bot class."""

    def __init__(self):
        """Initialize the Discord bot."""
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.dm_messages = True

        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )

        # Initialize database
        self.db = Database()

        # Initialize plugin manager
        self.plugin_manager = PluginManager(self)

        # Store guild reference
        self.guild_id = Config.GUILD_ID
        self.guild: discord.Guild | None = None

    async def setup_hook(self) -> None:
        """Setup hook called when the bot is starting."""
        logger.info("Bot is setting up...")

        # Load plugins
        journaling_plugin = JournalingPlugin(self)
        await self.plugin_manager.load_plugin(journaling_plugin)

        logger.info("Bot setup complete")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

        # Get guild reference
        self.guild = self.get_guild(self.guild_id)
        if not self.guild:
            logger.error(f"Could not find guild with ID {self.guild_id}")
            return

        logger.info(f"Connected to guild: {self.guild.name}")
        logger.info("Bot is ready!")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Handle bot errors."""
        logger.error(f"Error in {event_method}", exc_info=True)

    async def close(self) -> None:
        """Cleanup when bot is shutting down."""
        logger.info("Bot is shutting down...")
        await self.plugin_manager.unload_all()
        await super().close()


def main():
    """Main entry point for the bot."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")

        # Create and run bot
        bot = DiscordBot()
        bot.run(Config.DISCORD_BOT_TOKEN)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
