"""Base plugin system for extensible Discord bot."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """Base class for bot plugins."""

    def __init__(self, bot: 'commands.Bot'):
        """Initialize the plugin.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def setup(self) -> None:
        """Setup the plugin. Called when the plugin is loaded."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Cleanup the plugin. Called when the plugin is unloaded."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass


class PluginManager:
    """Manages bot plugins."""

    def __init__(self, bot: 'commands.Bot'):
        """Initialize the plugin manager.

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.plugins: dict[str, Plugin] = {}
        self.logger = logging.getLogger(__name__)

    async def load_plugin(self, plugin: Plugin) -> None:
        """Load a plugin.

        Args:
            plugin: The plugin instance to load
        """
        try:
            await plugin.setup()
            self.plugins[plugin.name] = plugin
            self.logger.info(f"Loaded plugin: {plugin.name}")
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin.name}: {e}")
            raise

    async def unload_plugin(self, plugin_name: str) -> None:
        """Unload a plugin.

        Args:
            plugin_name: The name of the plugin to unload
        """
        if plugin_name not in self.plugins:
            self.logger.warning(f"Plugin {plugin_name} not found")
            return

        try:
            plugin = self.plugins[plugin_name]
            await plugin.teardown()
            del self.plugins[plugin_name]
            self.logger.info(f"Unloaded plugin: {plugin_name}")
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            raise

    def get_plugin(self, plugin_name: str) -> Plugin | None:
        """Get a plugin by name.

        Args:
            plugin_name: The name of the plugin

        Returns:
            The plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for plugin_name in list(self.plugins.keys()):
            await self.unload_plugin(plugin_name)
