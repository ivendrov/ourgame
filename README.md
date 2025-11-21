# Discord Journaling Bot Framework

A flexible Discord bot framework for building collaborative journaling games and other multi-user experiences. The framework includes a starter journaling game where participants write daily journals to unlock access to a shared channel.

## Features

### Core Framework
- **Plugin System**: Easily extensible architecture for adding new features
- **Supabase Integration**: Real-time database storage with PostgreSQL
- **Configuration Management**: Environment-based configuration
- **Event-Driven Architecture**: React to Discord events with custom handlers

### Journaling Game (Starter Plugin)
- **Private Journal Channels**: Each participant gets a private channel for writing
- **Daily Word Count**: Track words written per day (default: 500 words required)
- **Shared Channel Access**: Automatic access control based on daily word count
- **AI-Powered Insights**: Run LLM prompts over all journals (anonymized)
- **Daily Reset**: Automatic access revocation at end of day

## Architecture

```
ourgame/
├── src/
│   ├── bot.py              # Main bot implementation
│   ├── config.py           # Configuration management
│   ├── database.py         # Supabase database interface
│   ├── plugin_base.py      # Plugin system base classes
│   └── plugins/
│       └── journaling.py   # Journaling game plugin
├── database/
│   └── schema.sql          # Database schema
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
└── README.md              # This file
```

## Setup

### Prerequisites
- Python 3.10 or higher
- Discord Bot Token (from Discord Developer Portal)
- Supabase Account and Project
- Google Gemini API Key

### 1. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" tab and create a bot
4. Enable the following **Privileged Gateway Intents**:
   - Server Members Intent
   - Message Content Intent
5. Copy the bot token
6. Go to OAuth2 > URL Generator:
   - Select scopes: `bot`, `applications.commands`
   - Select bot permissions:
     - `Manage Channels` (to create journal channels)
     - `Manage Permissions` (to control access to shared channel)
     - `Read Messages/View Channels`
     - `Send Messages`
     - `Read Message History`
7. Use the generated URL to invite the bot to your server

### 2. Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Project Settings > API to get your URL and anon key
3. Go to SQL Editor and run the schema from `database/schema.sql`
4. Enable real-time for the tables (optional but recommended):
   - Go to Database > Replication
   - Enable replication for `users`, `journal_entries`, and `daily_stats` tables

### 3. Google Gemini API Setup

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Copy the key for configuration

### 4. Create Shared Channel

1. In your Discord server, create a text channel (e.g., `#shared-journal`)
2. Set default permissions so that `@everyone` cannot see this channel
3. **IMPORTANT**: Give the bot explicit permissions in this channel:
   - Right-click the channel > Edit Channel > Permissions
   - Add the bot role or bot user
   - Enable: `View Channel`, `Send Messages`, `Read Message History`, and **`Manage Permissions`**
   - The bot MUST have `Manage Permissions` to control user access to this channel
4. Copy the channel ID (right-click channel > Copy ID - enable Developer Mode if needed)
5. Get your server (guild) ID the same way

### 5. Install and Configure

```bash
# Clone the repository
git clone <your-repo-url>
cd ourgame

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 6. Configuration (.env)

```env
# Discord Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GUILD_ID=your_discord_server_id_here
SHARED_CHANNEL_ID=your_shared_channel_id_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Bot Configuration
DAILY_WORD_REQUIREMENT=500
TIMEZONE=America/New_York
```

### 7. Run the Bot

```bash
python main.py
```

## Usage

### For Participants

1. **Create Journal Channel**: Send a DM to the bot, and it will create your private journal channel
2. **Write Daily**: Write at least 500 words (configurable) in your journal channel each day
3. **Access Shared Channel**: Once you meet the daily requirement, you'll automatically get access to the shared channel
4. **Use AI Commands**: In the shared channel, use `/gemini <prompt>` to run prompts over all journals

### Example Commands

```
/gemini What are the common themes in today's journals?
/gemini Summarize the mood across all entries
/gemini What challenges did people face today?
```

## Extending the Framework

### Creating a New Plugin

1. Create a new file in `src/plugins/your_plugin.py`
2. Inherit from the `Plugin` base class:

```python
from src.plugin_base import Plugin
from discord.ext import commands

class YourPlugin(Plugin):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @property
    def name(self) -> str:
        return "your_plugin"

    @property
    def description(self) -> str:
        return "Description of your plugin"

    async def setup(self) -> None:
        # Register event listeners
        self.bot.add_listener(self.on_some_event, 'on_message')

        # Register commands
        @self.bot.tree.command(name="yourcommand")
        async def your_command(interaction: discord.Interaction):
            await interaction.response.send_message("Hello!")

        await self.bot.tree.sync()

    async def teardown(self) -> None:
        # Cleanup
        pass

    async def on_some_event(self, message):
        # Handle events
        pass
```

3. Load your plugin in `src/bot.py`:

```python
from src.plugins.your_plugin import YourPlugin

# In setup_hook:
your_plugin = YourPlugin(self)
await self.plugin_manager.load_plugin(your_plugin)
```

### Database Access

All plugins have access to `self.bot.db` which provides:

```python
# User operations
await self.bot.db.get_or_create_user(discord_id, username)
await self.bot.db.get_user_by_discord_id(discord_id)
await self.bot.db.get_all_users_with_journals()

# Journal operations
await self.bot.db.create_journal_entry(discord_id, message_id, channel_id, content, word_count)
await self.bot.db.get_journal_entries_for_date(discord_id, date)
await self.bot.db.get_all_journal_entries_for_date(date)

# Stats operations
await self.bot.db.get_or_create_daily_stats(discord_id, date)
await self.bot.db.update_daily_stats(discord_id, date, total_words, has_access)
```

## Future Enhancement Ideas

- **Custom Bot Commands**: Allow users to register their own commands
- **Thread Creation**: Automatically group users into private threads based on journal content
- **Analytics Dashboard**: Web dashboard for viewing stats and insights
- **Multi-Server Support**: Run multiple independent games across servers
- **Scheduled Prompts**: Automatic daily prompts or questions
- **Streak Tracking**: Track consecutive days of writing
- **Achievement System**: Badges and rewards for milestones
- **Export Features**: Export journals to PDF, markdown, etc.

## Troubleshooting

### Bot doesn't respond to DMs
- Ensure Message Content Intent is enabled in Discord Developer Portal
- Check that the bot is online and connected

### Channel permissions issues / "403 Forbidden (error code: 50013): Missing Permissions"
- Make sure the bot has "Manage Channels" and "Manage Permissions" in the server
- **Most common issue**: The bot needs explicit "Manage Permissions" on the shared channel itself
  - Go to the shared channel > Edit Channel > Permissions
  - Add the bot and enable "Manage Permissions"
- Verify the bot role is high enough in the role hierarchy
- Check the bot logs for specific permission errors - they will indicate which channel needs attention

### Database errors
- Verify Supabase credentials in .env
- Check that schema.sql was run successfully
- Ensure network connectivity to Supabase

### Gemini API errors
- Verify API key is correct
- Check rate limits and quotas
- Ensure the API is enabled in your Google Cloud project

## Contributing

Contributions are welcome! This framework is designed to be extended by the community. Feel free to:
- Create new plugins
- Improve existing features
- Add documentation
- Report bugs
- Suggest enhancements

## License

MIT License - feel free to use and modify for your own projects.
