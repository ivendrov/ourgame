"""Journaling plugin for Discord bot."""
import discord
from discord.ext import commands, tasks
from datetime import datetime, date
from typing import Optional
import google.generativeai as genai
from src.plugin_base import Plugin
from src.config import Config
import logging

logger = logging.getLogger(__name__)


class JournalingPlugin(Plugin):
    """Plugin for managing journaling functionality."""

    def __init__(self, bot: commands.Bot):
        """Initialize the journaling plugin."""
        super().__init__(bot)

        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(Config.GEMINI_MODEL)

    @property
    def name(self) -> str:
        """Plugin name."""
        return "journaling"

    @property
    def description(self) -> str:
        """Plugin description."""
        return "Manages journal channels, word counting, and access control"

    async def setup(self) -> None:
        """Setup the plugin."""
        # Register event listeners
        self.bot.add_listener(self.on_message, 'on_message')

        # Register commands
        @self.bot.tree.command(name="gemini", description="Run a prompt over all journals")
        async def gemini_command(interaction: discord.Interaction, prompt: str):
            await self.handle_gemini_command(interaction, prompt)

        # Sync commands with Discord
        await self.bot.tree.sync()

        # Start background tasks
        self.check_daily_reset.start()

        self.logger.info("Journaling plugin setup complete")

    async def teardown(self) -> None:
        """Cleanup the plugin."""
        self.check_daily_reset.cancel()
        self.bot.remove_listener(self.on_message, 'on_message')
        self.logger.info("Journaling plugin teardown complete")

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Handle DMs - create journal channel
        if isinstance(message.channel, discord.DMChannel):
            await self.handle_dm(message)
            return

        # Handle messages in journal channels
        if await self.is_journal_channel(message.channel):
            await self.handle_journal_message(message)

    async def handle_dm(self, message: discord.Message) -> None:
        """Handle DM to create journal channel."""
        try:
            user = message.author

            # Create or get user first (atomic operation)
            db_user = await self.bot.db.get_or_create_user(user.id, user.name)

            # Check if user already has a journal channel
            if db_user.get('journal_channel_id'):
                channel = self.bot.guild.get_channel(db_user['journal_channel_id'])
                if channel:
                    await message.reply(
                        f"You already have a journal channel: {channel.mention}\n"
                        f"Please write your journal entries there!"
                    )
                    return
                # Channel was deleted, clear the ID
                await self.bot.db.update_user_journal_channel(user.id, None)

            # Create journal channel (checks for duplicates)
            channel = await self.create_journal_channel(user)

            # Update user's journal channel ID (only if not already set by another instance)
            updated = await self.bot.db.update_user_journal_channel(user.id, channel.id, only_if_null=True)

            if not updated:
                # Another instance already created a channel, use that one instead
                db_user = await self.bot.db.get_user_by_discord_id(user.id)
                if db_user and db_user.get('journal_channel_id'):
                    existing_channel = self.bot.guild.get_channel(db_user['journal_channel_id'])
                    if existing_channel and existing_channel.id != channel.id:
                        # Delete the duplicate channel we just created
                        await channel.delete()
                        channel = existing_channel

            # Send confirmation
            await message.reply(
                f"Created your journal channel: {channel.mention}\n"
                f"Write at least {Config.DAILY_WORD_REQUIREMENT} words per day to access the shared channel!"
            )

            await channel.send(
                f"Welcome to your journal, {user.mention}! 📔\n\n"
                f"Write at least **{Config.DAILY_WORD_REQUIREMENT} words** here each day to unlock access to the shared channel.\n"
                f"All your messages in this channel count toward your daily word count."
            )

        except Exception as e:
            self.logger.error(f"Error handling DM from {message.author}: {e}")
            await message.reply("Sorry, there was an error creating your journal channel. Please contact an admin.")

    async def create_journal_channel(self, user: discord.User) -> discord.TextChannel:
        """Create a private journal channel for a user."""
        guild = self.bot.guild
        if not guild:
            raise ValueError("Guild not found")

        # Create channel name
        channel_name = f"journal-{user.name}".lower().replace(" ", "-")

        # Check if channel already exists
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            # Verify user has access to it
            user_permissions = existing_channel.permissions_for(guild.get_member(user.id))
            if user_permissions.read_messages:
                self.logger.info(f"Found existing journal channel {channel_name} for user {user.name}")
                return existing_channel

        # Set permissions - only user and bot can see
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Create channel
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"Private journal for {user.name}"
        )

        self.logger.info(f"Created journal channel {channel.name} for user {user.name}")
        return channel

    async def is_journal_channel(self, channel: discord.TextChannel) -> bool:
        """Check if a channel is a journal channel."""
        if not isinstance(channel, discord.TextChannel):
            return False

        # Check if channel name starts with "journal-"
        return channel.name.startswith("journal-")

    async def handle_journal_message(self, message: discord.Message) -> None:
        """Handle a message in a journal channel."""
        try:
            user_id = message.author.id
            content = message.content
            word_count = len(content.split())

            # Skip messages with no words
            if word_count == 0:
                return

            # Store journal entry
            await self.bot.db.create_journal_entry(
                discord_id=user_id,
                username=message.author.name,
                message_id=message.id,
                channel_id=message.channel.id,
                content=content,
                word_count=word_count
            )

            # Update daily stats and get the updated totals
            total_words = await self.update_user_daily_stats(user_id)

            # Send feedback message
            if total_words >= Config.DAILY_WORD_REQUIREMENT:
                # Grant access to shared channel
                shared_channel = self.bot.guild.get_channel(Config.SHARED_CHANNEL_ID)
                if shared_channel:
                    member = self.bot.guild.get_member(user_id)
                    if member:
                        try:
                            await shared_channel.set_permissions(
                                member,
                                read_messages=True,
                                send_messages=True
                            )
                            # Congratulate and link to the channel
                            await message.reply(
                                f"🎉 Congratulations! You've written **{total_words}** words today and unlocked access to {shared_channel.mention}!"
                            )
                        except discord.Forbidden:
                            self.logger.error(f"Failed to grant permissions to {member.name}: Missing permissions")
                            await message.reply(
                                f"🎉 You've written **{total_words}** words today! (Note: Unable to automatically grant channel access - please contact an admin)"
                            )
                        except Exception as e:
                            self.logger.error(f"Error granting channel access to {member.name}: {e}")
                            await message.reply(
                                f"🎉 You've written **{total_words}** words today! (Note: There was an error granting channel access)"
                            )
                    else:
                        await message.reply(
                            f"🎉 Congratulations! You've written **{total_words}** words today and unlocked access to the shared channel!"
                        )
                else:
                    self.logger.error(f"Shared channel {Config.SHARED_CHANNEL_ID} not found")
                    await message.reply(
                        f"🎉 Congratulations! You've written **{total_words}** words today!"
                    )
            else:
                # Show remaining words needed
                remaining = Config.DAILY_WORD_REQUIREMENT - total_words
                await message.reply(
                    f"✍️ **{total_words}** words written today. **{remaining}** more to unlock the shared channel!"
                )

            self.logger.debug(f"Recorded journal entry for user {user_id}: {word_count} words")

        except Exception as e:
            self.logger.error(f"Error handling journal message: {e}")

    async def update_user_daily_stats(self, discord_id: int) -> int:
        """Update daily stats for a user.

        Returns:
            Total word count for the day
        """
        try:
            today = self.get_current_date()

            # Get today's journal entries
            entries = await self.bot.db.get_journal_entries_for_date(discord_id, today)

            # Calculate total words
            total_words = sum(entry['word_count'] for entry in entries)

            # Check if user meets requirement
            has_access = total_words >= Config.DAILY_WORD_REQUIREMENT

            # Update or create daily stats
            await self.bot.db.get_or_create_daily_stats(discord_id, today)
            await self.bot.db.update_daily_stats(discord_id, today, total_words, has_access)

            self.logger.debug(f"Updated daily stats for user {discord_id}: {total_words} words, access={has_access}")

            return total_words

        except Exception as e:
            self.logger.error(f"Error updating daily stats for user {discord_id}: {e}")
            return 0

    def get_current_date(self) -> date:
        """Get current date in configured timezone."""
        return datetime.now(Config.TIMEZONE).date()

    @tasks.loop(hours=1)
    async def check_daily_reset(self) -> None:
        """Check if we need to reset daily access (new day)."""
        try:
            today = self.get_current_date()
            now = datetime.now(Config.TIMEZONE)

            # Check if it's a new day and past midnight
            if now.hour == 0:
                # Revoke access from shared channel for all users
                shared_channel = self.bot.guild.get_channel(Config.SHARED_CHANNEL_ID)
                if shared_channel:
                    all_users = await self.bot.db.get_all_users_with_journals()
                    for user_data in all_users:
                        member = self.bot.guild.get_member(user_data['discord_id'])
                        if member:
                            await shared_channel.set_permissions(member, overwrite=None)

                    self.logger.info(f"Reset daily access for new day: {today}")

        except Exception as e:
            self.logger.error(f"Error in daily reset check: {e}")

    @check_daily_reset.before_loop
    async def before_check_daily_reset(self):
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()

    async def handle_gemini_command(self, interaction: discord.Interaction, prompt: str) -> None:
        """Handle /gemini command to run prompts over all journals."""
        try:
            # Check if command is used in the shared channel
            if interaction.channel_id != Config.SHARED_CHANNEL_ID:
                shared_channel = self.bot.guild.get_channel(Config.SHARED_CHANNEL_ID)
                channel_mention = shared_channel.mention if shared_channel else "the shared journaling channel"
                await interaction.response.send_message(
                    f"The /gemini command can only be used in {channel_mention}!",
                    ephemeral=True
                )
                return

            # Check if user has access today
            today = self.get_current_date()
            user_stats = await self.bot.db.get_or_create_daily_stats(interaction.user.id, today)

            if not user_stats.get('has_access'):
                await interaction.response.send_message(
                    f"You need to write {Config.DAILY_WORD_REQUIREMENT} words in your journal today to use this command!",
                    ephemeral=True
                )
                return

            # Defer response as this might take a while
            await interaction.response.defer()

            # Get all journal entries for today
            entries = await self.bot.db.get_all_journal_entries_for_date(today)

            if not entries:
                await interaction.followup.send("No journal entries found for today!")
                return

            # Group entries by user
            from collections import defaultdict
            users_journals = defaultdict(list)

            for entry in entries:
                user_key = (entry['discord_id'], entry['discord_username'])
                users_journals[user_key].append(entry)

            # Format journals grouped by user
            journal_texts = []
            for (discord_id, username), user_entries in users_journals.items():
                # Sort entries by timestamp for this user
                user_entries_sorted = sorted(user_entries, key=lambda e: e['created_at'])

                # Concatenate all entries for this user
                user_journal_text = "\n\n".join(entry['content'] for entry in user_entries_sorted)

                journal_texts.append(f"{username}'s journal:\n{user_journal_text}")

            aggregated_journals = "\n\n---\n\n".join(journal_texts)

            # Create prompt for Gemini
            full_prompt = f"""You have access to journal entries from multiple users from today.
Here are the journals:

{aggregated_journals}

User's request: {prompt}

Please respond to the user's request based on these journal entries."""

            # Call Gemini API
            response = self.gemini_model.generate_content(full_prompt)

            # Send response (split if too long)
            response_text = response.text
            if len(response_text) > 2000:
                # Split into chunks
                chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.channel.send(chunk)
            else:
                await interaction.followup.send(response_text)

        except Exception as e:
            self.logger.error(f"Error handling gemini command: {e}")
            await interaction.followup.send(f"Sorry, there was an error processing your request: {str(e)}")
